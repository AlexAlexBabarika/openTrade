"""Unit tests for position_metrics helpers."""

from __future__ import annotations

import pytest

from backend.market.position_metrics import (
    PositionMetricsError,
    compute_risk_reward_ratio,
)


def test_long_rr():
    assert compute_risk_reward_ratio(
        "long", entry_price=100.0, stop_price=95.0, target_price=110.0
    ) == pytest.approx(2.0)


def test_short_rr():
    assert compute_risk_reward_ratio(
        "short", entry_price=100.0, stop_price=105.0, target_price=90.0
    ) == pytest.approx(2.0)


def test_long_invalid_stop_above_entry():
    with pytest.raises(PositionMetricsError, match="long position"):
        compute_risk_reward_ratio("long", 100.0, 101.0, 110.0)


def test_short_invalid_target_above_entry():
    with pytest.raises(PositionMetricsError, match="short position"):
        compute_risk_reward_ratio("short", 100.0, 105.0, 101.0)
