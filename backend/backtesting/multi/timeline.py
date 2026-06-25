"""The aligned multi-symbol timeline.

Per-symbol OHLCV frames are merged into one time-ordered stream of MULTI_BAR
events — one event per distinct timestamp, carrying every symbol that closed a
bar at that time. ``MultiBarSeries`` holds one look-ahead-guarded ``BarSeries``
cursor per symbol and advances only the symbols present in the consumed event,
so a data gap in one symbol can never reveal future bars of another.

Determinism: symbols are iterated in sorted order everywhere (event ``bars``
insertion order, ``symbols``), so no output depends on input dict ordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import polars as pl

from backend.backtesting.context import BarSeries, BarsView
from backend.backtesting.loop import bar_events_from_frame
from backend.backtesting.types import Bar


@dataclass(frozen=True, slots=True)
class MultiBarEvent:
    """All bars that closed at one timestamp, keyed by symbol (sorted order)."""

    time: datetime
    bars: dict[str, Bar]


def events_from_frames(frames: dict[str, pl.DataFrame]) -> list[MultiBarEvent]:
    """Merge per-symbol OHLCV frames into time-ordered ``MultiBarEvent``s.

    Each frame carries the repo's candle schema (``timestamp/open/high/low/
    close/volume``). The result covers the union of all timestamps; an event's
    ``bars`` holds only the symbols that have a bar at that time.
    """
    per_time: dict[datetime, dict[str, Bar]] = {}
    for symbol in sorted(frames):
        for event in bar_events_from_frame(frames[symbol]):
            per_time.setdefault(event.time, {})[symbol] = event.bar
    return [MultiBarEvent(time=t, bars=per_time[t]) for t in sorted(per_time)]


class MultiBarSeries:
    """One guarded bar cursor per symbol, advanced together by the engine.

    Built from the same event list the engine consumes; ``advance(event)``
    must be called once per consumed event, in order. Reading a symbol returns
    its ``BarsView`` (the same look-ahead-guarded view single-symbol
    strategies get), whose length is the bars revealed for that symbol so far.
    """

    def __init__(self, events: Iterable[MultiBarEvent]) -> None:
        per_symbol: dict[str, list[Bar]] = {}
        for event in events:
            for symbol, bar in event.bars.items():
                per_symbol.setdefault(symbol, []).append(bar)
        self._series = {s: BarSeries(per_symbol[s]) for s in sorted(per_symbol)}
        self._views = {s: BarsView(series) for s, series in self._series.items()}

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(self._series)

    def advance(self, event: MultiBarEvent) -> None:
        """Reveal the next bar for every symbol present in ``event``."""
        for symbol in event.bars:
            self._series[symbol].advance()

    def __getitem__(self, symbol: str) -> BarsView:
        try:
            return self._views[symbol]
        except KeyError:
            raise KeyError(f"unknown symbol {symbol!r}") from None

    def __contains__(self, symbol: str) -> bool:
        return symbol in self._views
