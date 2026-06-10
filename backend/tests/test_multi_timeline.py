"""
The aligned multi-symbol timeline merges per-symbol OHLCV frames into one
time-ordered stream of MULTI_BAR events (one per distinct timestamp, carrying
every symbol that closed a bar then). MultiBarSeries keeps a look-ahead-guarded
cursor per symbol: a symbol's history only grows when an event containing that
symbol is consumed, so gaps in one symbol never leak future bars of another.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from backend.backtesting.errors import LookAheadError
from backend.backtesting.multi.timeline import (
    MultiBarEvent,
    MultiBarSeries,
    events_from_frames,
)


def _frame(
    closes: list[float], *, start_day: int = 1, skip_days: set[int] | None = None
) -> pl.DataFrame:
    """Daily frame; ``skip_days`` are 0-based offsets to omit (data gaps)."""
    start = datetime(2024, 1, start_day, tzinfo=timezone.utc)
    skip = skip_days or set()
    rows = [
        (start + timedelta(days=i), c) for i, c in enumerate(closes) if i not in skip
    ]
    return pl.DataFrame(
        {
            "timestamp": [t for t, _ in rows],
            "open": [c for _, c in rows],
            "high": [c + 1 for _, c in rows],
            "low": [c - 1 for _, c in rows],
            "close": [c for _, c in rows],
            "volume": [1000.0] * len(rows),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


def test_events_are_the_union_of_timestamps_in_ascending_order() -> None:
    frames = {
        "AAPL": _frame([10.0, 11.0, 12.0]),
        "MSFT": _frame([20.0, 21.0], start_day=2),
    }
    events = events_from_frames(frames)
    assert [e.time.day for e in events] == [1, 2, 3]
    assert all(isinstance(e, MultiBarEvent) for e in events)
    assert list(events[0].bars) == ["AAPL"]
    assert list(events[1].bars) == ["AAPL", "MSFT"]
    assert list(events[2].bars) == ["AAPL", "MSFT"]
    assert events[1].bars["MSFT"].close == 20.0


def test_symbol_order_within_an_event_is_sorted_regardless_of_input_order() -> None:
    a, b = _frame([10.0]), _frame([20.0])
    assert list(events_from_frames({"MSFT": b, "AAPL": a})[0].bars) == ["AAPL", "MSFT"]
    assert list(events_from_frames({"AAPL": a, "MSFT": b})[0].bars) == ["AAPL", "MSFT"]


def test_series_reveals_bars_only_as_events_are_consumed() -> None:
    frames = {
        "AAPL": _frame([10.0, 11.0, 12.0]),
        "MSFT": _frame([20.0, 21.0], start_day=2),
    }
    events = events_from_frames(frames)
    series = MultiBarSeries(events)
    assert series.symbols == ("AAPL", "MSFT")

    series.advance(events[0])
    assert len(series["AAPL"]) == 1
    assert len(series["MSFT"]) == 0  # MSFT has not closed a bar yet

    series.advance(events[1])
    assert len(series["AAPL"]) == 2
    assert len(series["MSFT"]) == 1
    assert series["MSFT"][-1].close == 20.0
    assert series["AAPL"][-1].close == 11.0


def test_gap_in_one_symbol_does_not_advance_it() -> None:
    frames = {
        "AAPL": _frame([10.0, 11.0, 12.0]),
        "MSFT": _frame([20.0, 21.0, 22.0], skip_days={1}),
    }
    events = events_from_frames(frames)
    series = MultiBarSeries(events)
    series.advance(events[0])
    series.advance(events[1])  # day 2: AAPL only
    assert len(series["AAPL"]) == 2
    assert len(series["MSFT"]) == 1
    series.advance(events[2])
    assert series["MSFT"][-1].close == 22.0


def test_future_read_raises_look_ahead_error() -> None:
    events = events_from_frames({"AAPL": _frame([10.0, 11.0, 12.0])})
    series = MultiBarSeries(events)
    series.advance(events[0])
    with pytest.raises(LookAheadError):
        series["AAPL"][1]


def test_unknown_symbol_raises_key_error() -> None:
    events = events_from_frames({"AAPL": _frame([10.0])})
    series = MultiBarSeries(events)
    with pytest.raises(KeyError):
        series["TSLA"]
    assert "AAPL" in series
    assert "TSLA" not in series
