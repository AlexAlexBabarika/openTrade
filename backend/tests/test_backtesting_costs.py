"""
Slippage and half-spread move the effective fill price adverse to the trade
direction (a buy fills higher, a sell lower); commission is a separate currency
charge. The recorded cost fields are currency totals for reporting. Defaults are
conservative (non-zero); frictionless is an explicit opt-in.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.backtesting.costs import (
    BpsCommission,
    Costs,
    FixedBpsHalfSpread,
    FixedBpsSlippage,
    PerShareCommission,
)
from backend.backtesting.orders import Broker
from backend.backtesting.types import Bar, OrderType, Side


def _bar(o: float = 100.0, c: float = 100.0) -> Bar:
    return Bar(
        time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=o,
        high=max(o, c) + 1,
        low=min(o, c) - 1,
        close=c,
        volume=1000.0,
    )


# --- individual models -----------------------------------------------------


def test_fixed_bps_slippage_is_bps_of_reference_price() -> None:
    assert FixedBpsSlippage(10.0).slippage(100.0, Side.BUY, _bar()) == 0.1


def test_per_share_commission_scales_with_quantity() -> None:
    assert PerShareCommission(0.01).commission(100.0, 10.0) == 0.1


def test_bps_commission_scales_with_notional() -> None:
    # 10 bps of a 100 * 10 = 1_000 notional -> 1.0, independent of share count.
    assert BpsCommission(10.0).commission(100.0, 10.0) == 1.0


def test_default_commission_is_notional_scaled_not_per_share() -> None:
    # Default commission is bps-based, so two fills of equal notional cost the
    # same regardless of share count — back-adjusted (tiny-price, huge-quantity)
    # bars no longer inflate it. Per-share commission would differ ~10_000x here.
    _, _, _, penny = Costs.default().apply(
        reference_price=0.01, side=Side.BUY, quantity=1_000_000.0, bar=_bar()
    )
    _, _, _, normal = Costs.default().apply(
        reference_price=100.0, side=Side.BUY, quantity=100.0, bar=_bar()
    )
    assert penny == pytest.approx(normal)


def test_fixed_bps_half_spread_is_bps_of_reference_price() -> None:
    assert FixedBpsHalfSpread(5.0).half_spread(100.0, _bar()) == 0.05


# --- aggregate apply -------------------------------------------------------


def _costs() -> Costs:
    return Costs(
        slippage=FixedBpsSlippage(10.0),  # 0.1 / share at 100
        commission=PerShareCommission(0.01),  # 0.1 for 10 shares
        spread=FixedBpsHalfSpread(5.0),  # 0.05 / share at 100
    )


def test_buy_fill_price_includes_slippage_and_spread_adverse() -> None:
    price, *_ = _costs().apply(
        reference_price=100.0, side=Side.BUY, quantity=10.0, bar=_bar()
    )
    assert price == 100.15  # 100 + 0.1 + 0.05


def test_sell_fill_price_includes_slippage_and_spread_adverse() -> None:
    price, *_ = _costs().apply(
        reference_price=100.0, side=Side.SELL, quantity=10.0, bar=_bar()
    )
    assert price == 99.85  # 100 - 0.1 - 0.05


def test_recorded_costs_are_currency_totals() -> None:
    _, slippage, spread_cost, commission = _costs().apply(
        reference_price=100.0, side=Side.BUY, quantity=10.0, bar=_bar()
    )
    assert slippage == 1.0  # 0.1 * 10
    assert spread_cost == 0.5  # 0.05 * 10
    assert commission == 0.1  # 0.01 * 10


# --- defaults / opt-out ----------------------------------------------------


def test_frictionless_costs_are_zero() -> None:
    price, slippage, spread_cost, commission = Costs.frictionless().apply(
        reference_price=100.0, side=Side.BUY, quantity=10.0, bar=_bar()
    )
    assert (price, slippage, spread_cost, commission) == (100.0, 0.0, 0.0, 0.0)


def test_default_costs_are_conservative_nonzero() -> None:
    price, slippage, spread_cost, commission = Costs.default().apply(
        reference_price=100.0, side=Side.BUY, quantity=10.0, bar=_bar()
    )
    assert slippage > 0
    assert spread_cost > 0
    assert commission > 0
    assert price > 100.0


# --- broker integration ----------------------------------------------------


def test_broker_applies_costs_to_fills() -> None:
    broker = Broker(costs=_costs())
    broker.submit_order(
        side=Side.BUY, quantity=10.0, type=OrderType.MARKET, bar_index=0
    )
    fill = broker.process_bar(_bar(o=100.0, c=101.0), bar_index=1)[0]
    assert fill.reference_price == 100.0
    assert fill.price == 100.15
    assert fill.slippage == 1.0
    assert fill.spread_cost == 0.5
    assert fill.commission == 0.1


def test_broker_default_is_frictionless() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.BUY, quantity=10.0, type=OrderType.MARKET, bar_index=0
    )
    fill = broker.process_bar(_bar(o=100.0, c=101.0), bar_index=1)[0]
    assert fill.price == fill.reference_price == 100.0
    assert fill.slippage == fill.spread_cost == fill.commission == 0.0
