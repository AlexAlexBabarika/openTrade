"""
The engine reveals bars one at a time. ``ctx.bars`` exposes history up to and
including the current bar; any attempt to read further forward is the look-ahead
class of bug the engine exists to prevent, so it raises a clear LookAheadError
rather than silently succeeding
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.backtesting.context import BarSeries, Context
from backend.backtesting.errors import EngineError, LookAheadError
from backend.backtesting.types import Bar


def _bars(n: int) -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(
            time=start + timedelta(days=i),
            open=10.0 + i,
            high=11.0 + i,
            low=9.0 + i,
            close=10.5 + i,
            volume=1000.0,
        )
        for i in range(n)
    ]


def test_advance_reveals_bars_one_at_a_time() -> None:
    series = BarSeries(_bars(3))
    assert len(series) == 0
    series.advance()
    assert len(series) == 1
    series.advance()
    assert len(series) == 2


def test_ctx_time_is_current_bar_time() -> None:
    bars = _bars(3)
    series = BarSeries(bars)
    series.advance()
    series.advance()  # current index = 1
    ctx = Context(series)
    assert ctx.time == bars[1].time


def test_bars_exposes_history_up_to_and_including_current() -> None:
    bars = _bars(3)
    series = BarSeries(bars)
    series.advance()
    series.advance()  # current index = 1
    ctx = Context(series)
    assert len(ctx.bars) == 2
    assert ctx.bars[0] is bars[0]
    assert ctx.bars[1] is bars[1]
    assert ctx.bars[-1] is bars[1]
    assert ctx.bars[-2] is bars[0]


def test_iterating_bars_yields_only_revealed_history() -> None:
    bars = _bars(3)
    series = BarSeries(bars)
    series.advance()
    series.advance()  # current index = 1
    ctx = Context(series)
    assert list(ctx.bars) == bars[:2]


def test_reading_next_bar_raises_lookahead_error() -> None:
    bars = _bars(3)
    series = BarSeries(bars)
    series.advance()  # only bar 0 revealed; bar 1 exists but is the future
    ctx = Context(series)
    with pytest.raises(LookAheadError, match="future"):
        _ = ctx.bars[1]


def test_lookahead_error_is_an_engine_error() -> None:
    assert issubclass(LookAheadError, EngineError)


def test_time_before_first_bar_raises_engine_error() -> None:
    ctx = Context(BarSeries(_bars(3)))
    with pytest.raises(EngineError):
        _ = ctx.time
