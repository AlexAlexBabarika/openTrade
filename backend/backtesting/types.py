"""Core value types for the backtesting engine.

Foundational, immutable building blocks the event loop consumes. Order, fill,
and position types are defined alongside the tasks that exercise them so every
field traces to a behaviour under test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Bar:
    """A single closed OHLCV bar. ``time`` is the bar's close timestamp (UTC)."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class BarEvent:
    """A ``BAR`` event: a newly closed bar entering the event loop."""

    bar: Bar

    @property
    def time(self) -> datetime:
        return self.bar.time
