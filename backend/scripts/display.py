"""DisplayCollector: the `display(...)` callable injected into user scripts.

Translates user-friendly inputs (a polars Series aligned with the global
`time` series, a list of (time, value) tuples, a plain string, a dict)
into the strict ScriptOutput models.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
import polars as pl

from backend.scripts.output_models import (
    MAX_OUTPUTS_PER_RUN,
    MAX_ROWS_PER_SERIES,
    HistogramOutput,
    HistogramPoint,
    MarkerPoint,
    MarkersOutput,
    OverlayOutput,
    PaneOutput,
    ScriptOutput,
    SeriesPoint,
    TableOutput,
    TextOutput,
)


class DisplayError(ValueError):
    """Raised by DisplayCollector for malformed display() calls."""


def _to_unix_seconds(ts: Any) -> int:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return int(ts.timestamp())
    if isinstance(ts, (int, np.integer)):
        v = int(ts)
        return v // 1000 if v > 10**12 else v
    if isinstance(ts, (float, np.floating)):
        return int(ts)
    raise DisplayError(f"cannot convert timestamp of type {type(ts).__name__}")


def _pairs_to_series_points(pairs: Iterable[Any]) -> list[SeriesPoint]:
    out: list[SeriesPoint] = []
    for item in pairs:
        if isinstance(item, dict):
            t = item.get("time", item.get("timestamp"))
            v = item.get("value")
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            t, v = item
        else:
            raise DisplayError(f"unsupported point: {item!r}")
        out.append(SeriesPoint(time=_to_unix_seconds(t), value=float(v)))
        if len(out) > MAX_ROWS_PER_SERIES:
            raise DisplayError(f"series exceeds max rows ({MAX_ROWS_PER_SERIES})")
    return out


class DisplayCollector:
    """Callable invoked from user code as `display(kind, data, ...)`.

    Examples user code can write:
        display.line(price.rolling_mean(20), title="SMA20")
        display.pane(rsi, title="RSI", pane_id="rsi")
        display.histogram(macd_hist, title="MACD hist", pane_id="macd")
        display.markers(crossover(fast, slow), shape="arrowUp", color="lime")
        display.text("hello", level="info")
        display.table(["a","b"], [[1,2],[3,4]])
    """

    def __init__(self, time: pl.Series) -> None:
        self._time = time
        self._time_list = time.to_list()
        self._outputs: list[ScriptOutput] = []

    @property
    def outputs(self) -> list[ScriptOutput]:
        return self._outputs

    def _push(self, item: ScriptOutput) -> None:
        if len(self._outputs) >= MAX_OUTPUTS_PER_RUN:
            raise DisplayError(f"too many outputs (max {MAX_OUTPUTS_PER_RUN} per run)")
        self._outputs.append(item)

    def _series_to_points(self, series: pl.Series) -> list[SeriesPoint]:
        if len(series) != len(self._time_list):
            raise DisplayError(
                f"series length {len(series)} does not match time length "
                f"{len(self._time_list)}"
            )
        if len(series) > MAX_ROWS_PER_SERIES:
            raise DisplayError(
                f"series has {len(series)} rows; max allowed is {MAX_ROWS_PER_SERIES}"
            )
        out: list[SeriesPoint] = []
        for t, v in zip(self._time_list, series.to_list()):
            if v is None:
                continue
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                continue
            out.append(SeriesPoint(time=_to_unix_seconds(t), value=fv))
        return out

    def _coerce_series(self, data: Any) -> list[SeriesPoint]:
        if isinstance(data, pl.Series):
            return self._series_to_points(data)
        if isinstance(data, (list, tuple)):
            return _pairs_to_series_points(data)
        raise DisplayError(
            "data must be a polars Series or list of (time, value) pairs"
        )

    def _coerce_markers(self, data: Any) -> list[MarkerPoint]:
        if isinstance(data, pl.Series):
            if data.dtype != pl.Boolean:
                data = data.cast(pl.Boolean, strict=False)
            if len(data) != len(self._time_list):
                raise DisplayError(
                    f"marker series length {len(data)} does not match time length "
                    f"{len(self._time_list)}"
                )
            out: list[MarkerPoint] = []
            for t, v in zip(self._time_list, data.to_list()):
                if bool(v):
                    out.append(MarkerPoint(time=_to_unix_seconds(t)))
                if len(out) > MAX_ROWS_PER_SERIES:
                    raise DisplayError(
                        f"markers exceed max rows ({MAX_ROWS_PER_SERIES})"
                    )
            return out
        if isinstance(data, (list, tuple)):
            out2: list[MarkerPoint] = []
            for item in data:
                if isinstance(item, dict):
                    t = item.get("time", item.get("timestamp"))
                else:
                    t = item
                out2.append(MarkerPoint(time=_to_unix_seconds(t)))
                if len(out2) > MAX_ROWS_PER_SERIES:
                    raise DisplayError(
                        f"markers exceed max rows ({MAX_ROWS_PER_SERIES})"
                    )
            return out2
        raise DisplayError("markers data must be a boolean Series or list of times")

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        if not args:
            raise DisplayError("display() requires at least one argument")
        first = args[0]
        if isinstance(first, str):
            self.text(first, level=kwargs.get("level", "info"))
            return
        title = kwargs.pop("title", "series")
        self.line(first, title=title, **kwargs)

    def line(
        self,
        data: Any,
        *,
        title: str = "series",
        color: str | None = None,
        line_width: int | None = None,
        line_style: str | None = None,
    ) -> None:
        self._push(
            OverlayOutput(
                title=title,
                data=self._coerce_series(data),
                color=color,
                line_width=line_width,
                line_style=line_style,
            )
        )

    def pane(
        self,
        data: Any,
        *,
        title: str = "pane",
        color: str | None = None,
        height: int | None = None,
        pane_id: str | None = None,
    ) -> None:
        self._push(
            PaneOutput(
                title=title,
                data=self._coerce_series(data),
                color=color,
                height=height,
                pane_id=pane_id,
            )
        )

    def histogram(
        self,
        data: Any,
        *,
        title: str = "histogram",
        pane_id: str | None = None,
    ) -> None:
        pts = self._coerce_series(data)
        hist = [HistogramPoint(time=p.time, value=p.value) for p in pts]
        self._push(HistogramOutput(title=title, data=hist, pane_id=pane_id))

    def markers(
        self,
        data: Any,
        *,
        shape: str | None = None,
        position: str | None = None,
        color: str | None = None,
        text: str | None = None,
    ) -> None:
        self._push(
            MarkersOutput(
                data=self._coerce_markers(data),
                shape=shape,
                position=position,
                color=color,
                text=text,
            )
        )

    def table(self, columns: list[str], rows: list[list[Any]]) -> None:
        self._push(TableOutput(columns=list(columns), rows=[list(r) for r in rows]))

    def text(self, text: str, *, level: str = "info") -> None:
        if level not in ("info", "warn", "error"):
            level = "info"
        self._push(TextOutput(text=str(text), level=level))  # type: ignore[arg-type]
