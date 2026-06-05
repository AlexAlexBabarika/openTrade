"""
Covers the foundational, fully-determined types the event loop (T2) builds on:
the immutable ``Bar`` and the ``BarEvent`` that carries it through the loop.
Order/Fill/Position types land with the tasks that exercise them.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.backtesting.types import Bar, BarEvent


def _bar(**kw) -> Bar:
    base = dict(
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=10.0,
        high=11.0,
        low=9.0,
        close=10.5,
        volume=1000.0,
    )
    base.update(kw)
    return Bar(**base)


def test_bar_holds_ohlcv() -> None:
    b = _bar()
    assert b.open == 10.0
    assert b.high == 11.0
    assert b.low == 9.0
    assert b.close == 10.5
    assert b.volume == 1000.0
    assert b.time == datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_bar_is_immutable() -> None:
    b = _bar()
    with pytest.raises(Exception):
        b.close = 99.0  # type: ignore[misc]


def test_bar_event_carries_bar_and_exposes_its_time() -> None:
    b = _bar()
    ev = BarEvent(bar=b)
    assert ev.bar is b
    assert ev.time == b.time
