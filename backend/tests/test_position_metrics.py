"""Unit tests for position_metrics helpers."""

from __future__ import annotations

import pytest

from backend.market.position_metrics import (
    PositionMetricsError,
    compute_position_metrics,
)


def test_long_rr_and_qty_from_risk_amount():
    r = compute_position_metrics(
        "long",
        entry_price=100.0,
        stop_price=95.0,
        target_price=110.0,
        risk_amount=100.0,
    )
    assert r.risk_price_distance == 5.0
    assert r.reward_price_distance == 10.0
    assert r.risk_reward_ratio == pytest.approx(2.0)
    assert r.quantity == pytest.approx(20.0)
    assert r.profit_at_target == pytest.approx(200.0)
    assert r.loss_at_stop == pytest.approx(100.0)
    assert not r.quantity_capped_by_leverage


def test_short_rr():
    r = compute_position_metrics(
        "short",
        entry_price=100.0,
        stop_price=105.0,
        target_price=90.0,
    )
    assert r.risk_price_distance == 5.0
    assert r.reward_price_distance == 10.0
    assert r.risk_reward_ratio == pytest.approx(2.0)
    assert r.quantity is None


def test_long_invalid_stop_above_entry():
    with pytest.raises(PositionMetricsError, match="long position"):
        compute_position_metrics("long", 100.0, 101.0, 110.0)


def test_short_invalid_target_above_entry():
    with pytest.raises(PositionMetricsError, match="short position"):
        compute_position_metrics("short", 100.0, 105.0, 101.0)


def test_risk_percent_with_account():
    r = compute_position_metrics(
        "long",
        entry_price=50.0,
        stop_price=45.0,
        target_price=60.0,
        account_balance=10_000.0,
        risk_percent=1.0,
    )
    assert r.quantity == pytest.approx(20.0)


def test_leverage_caps_quantity():
    r = compute_position_metrics(
        "long",
        entry_price=100.0,
        stop_price=90.0,
        target_price=120.0,
        account_balance=1_000.0,
        risk_amount=500.0,
        leverage=1.0,
    )
    assert r.quantity_capped_by_leverage
    assert r.quantity == pytest.approx(10.0)


def test_explicit_quantity_skips_risk_sizing():
    r = compute_position_metrics(
        "long",
        entry_price=100.0,
        stop_price=95.0,
        target_price=110.0,
        quantity=2.0,
    )
    assert r.quantity == 2.0
    assert r.profit_at_target == pytest.approx(20.0)
    assert r.loss_at_stop == pytest.approx(10.0)
