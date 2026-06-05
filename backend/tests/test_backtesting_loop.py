"""
The loop turns a polars OHLCV frame into an ordered stream of BAR events and
owns a clock that advances only by consuming events. These two guarantees
(time-ordered emission, clock == current event time) are what eliminate the
look-ahead class of bugs the engine exists to prevent.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl

from backend.backtesting.loop import EventLoop, bar_events_from_frame
from backend.backtesting.types import BarEvent


def _frame(n: int = 5) -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(days=i) for i in range(n)]
    close = [10.0 + i for i in range(n)]
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": [1000.0] * n,
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


def test_builder_maps_each_row_to_a_bar_event() -> None:
    frame = _frame(3)
    events = bar_events_from_frame(frame)
    assert len(events) == 3
    assert all(isinstance(e, BarEvent) for e in events)
    first = events[0]
    assert first.bar.open == 10.0
    assert first.bar.high == 11.0
    assert first.bar.low == 9.0
    assert first.bar.close == 10.0
    assert first.bar.volume == 1000.0
    assert first.bar.time == datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_loop_emits_events_in_timestamp_order_even_when_input_shuffled() -> None:
    frame = _frame(5)
    shuffled = frame.sample(fraction=1.0, shuffle=True, seed=7)
    loop = EventLoop(bar_events_from_frame(shuffled))
    times = [ev.time for ev in loop]
    assert times == sorted(times)
    assert len(times) == 5


def test_clock_tracks_the_event_being_consumed() -> None:
    loop = EventLoop(bar_events_from_frame(_frame(3)))
    for ev in loop:
        assert loop.time == ev.time


def test_clock_is_none_before_any_event_is_consumed() -> None:
    loop = EventLoop(bar_events_from_frame(_frame(3)))
    assert loop.time is None
