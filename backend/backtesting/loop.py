"""The deterministic event loop.

A single ordered stream of events drives the simulation. The clock advances
*only* by consuming an event, and always equals the time of the event being
consumed — strategy code reads this clock, never ``datetime.now()``, which is
what structurally prevents look-ahead.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Iterator

import polars as pl

from backend.backtesting.types import Bar, BarEvent


def bar_events_from_frame(df: pl.DataFrame) -> list[BarEvent]:
    """Convert a polars OHLCV frame into BAR events.

    The frame is expected to carry ``timestamp/open/high/low/close/volume``
    columns (timestamp UTC), matching the repo's candle schema.
    """
    return [
        BarEvent(
            bar=Bar(
                time=row["timestamp"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
        )
        for row in df.iter_rows(named=True)
    ]


class EventLoop:
    """Owns the clock and emits events in time order.

    Iterating the loop yields each event in ascending time order, updating the
    clock (``time``) to the event being consumed. Before the first event is
    consumed the clock is ``None``.
    """

    def __init__(self, events: Iterable[BarEvent]) -> None:
        self._pending: list[BarEvent] = sorted(events, key=lambda e: e.time)
        self._time: datetime | None = None

    @property
    def time(self) -> datetime | None:
        return self._time

    def __iter__(self) -> Iterator[BarEvent]:
        for event in self._pending:
            self._time = event.time
            yield event
