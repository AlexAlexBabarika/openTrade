"""
The universe defines which symbols a portfolio strategy may see at each point
in time. Membership is interval-based (start inclusive, end exclusive) so the
engine can enforce that a strategy never reads a symbol before it joins or
after it leaves, and a symbol can leave and rejoin.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.backtesting.errors import UniverseError
from backend.backtesting.multi.universe import Membership, Universe


def _t(day: int) -> datetime:
    return datetime(2024, 1, day, tzinfo=timezone.utc)


def test_static_universe_is_always_active_and_sorted() -> None:
    u = Universe.static(["MSFT", "AAPL", "GOOG"])
    assert u.symbols == ("AAPL", "GOOG", "MSFT")
    assert u.active(_t(1)) == ("AAPL", "GOOG", "MSFT")
    assert u.active(_t(31)) == ("AAPL", "GOOG", "MSFT")


def test_membership_window_start_inclusive_end_exclusive() -> None:
    u = Universe([Membership("AAPL", start=_t(5), end=_t(10))])
    assert not u.is_active("AAPL", _t(4))
    assert u.is_active("AAPL", _t(5))
    assert u.is_active("AAPL", _t(9))
    assert not u.is_active("AAPL", _t(10))
    assert not u.is_active("AAPL", _t(11))


def test_open_ended_memberships() -> None:
    u = Universe(
        [
            Membership("AAPL"),  # forever
            Membership("MSFT", start=_t(3)),  # joins, never leaves
            Membership("GOOG", end=_t(3)),  # in from the start, then leaves
        ]
    )
    assert u.active(_t(1)) == ("AAPL", "GOOG")
    assert u.active(_t(3)) == ("AAPL", "MSFT")


def test_symbol_can_leave_and_rejoin() -> None:
    u = Universe(
        [
            Membership("AAPL", start=_t(1), end=_t(5)),
            Membership("AAPL", start=_t(10), end=_t(20)),
        ]
    )
    assert u.is_active("AAPL", _t(2))
    assert not u.is_active("AAPL", _t(7))
    assert u.is_active("AAPL", _t(10))
    assert u.symbols == ("AAPL",)


def test_unknown_symbol_is_never_active() -> None:
    u = Universe.static(["AAPL"])
    assert not u.is_active("TSLA", _t(1))


def test_empty_interval_rejected() -> None:
    with pytest.raises(UniverseError):
        Universe([Membership("AAPL", start=_t(5), end=_t(5))])
    with pytest.raises(UniverseError):
        Universe([Membership("AAPL", start=_t(6), end=_t(5))])


def test_overlapping_intervals_for_same_symbol_rejected() -> None:
    with pytest.raises(UniverseError):
        Universe(
            [
                Membership("AAPL", start=_t(1), end=_t(10)),
                Membership("AAPL", start=_t(5), end=_t(20)),
            ]
        )
    # An open end overlaps any later interval.
    with pytest.raises(UniverseError):
        Universe(
            [
                Membership("AAPL", start=_t(1)),
                Membership("AAPL", start=_t(5), end=_t(6)),
            ]
        )


def test_adjacent_intervals_are_allowed() -> None:
    u = Universe(
        [
            Membership("AAPL", start=_t(1), end=_t(5)),
            Membership("AAPL", start=_t(5), end=_t(9)),
        ]
    )
    assert u.is_active("AAPL", _t(5))


def test_empty_universe_rejected() -> None:
    with pytest.raises(UniverseError):
        Universe([])
    with pytest.raises(UniverseError):
        Universe.static([])
