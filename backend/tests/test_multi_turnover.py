"""
Turnover is the drag rebalancing inflicts: gross traded value relative to
equity. It is derived purely from fills and the equity curve (no engine
bookkeeping), as per-event fractions for the distribution view and as an
annualized figure for the headline number.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.backtesting.multi.book import PortfolioEquityPoint
from backend.backtesting.multi.turnover import annualized_turnover, per_event_turnover
from backend.backtesting.types import Fill, Side


def _fill(index: int, qty: float, price: float, side: Side = Side.BUY) -> Fill:
    return Fill(
        order_id=0,
        side=side,
        quantity=qty,
        price=price,
        reference_price=price,
        slippage=0.0,
        spread_cost=0.0,
        commission=0.0,
        submitted_index=index - 1,
        fill_index=index,
        reason="market",
        symbol="AAPL",
    )


def _curve(equities: list[float], *, days_apart: int = 1) -> list[PortfolioEquityPoint]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        PortfolioEquityPoint(
            time=start + timedelta(days=i * days_apart),
            equity=e,
            cash=e,
            holdings=0.0,
            weights={},
        )
        for i, e in enumerate(equities)
    ]


def test_per_event_turnover_groups_fills_by_event() -> None:
    curve = _curve([1_000.0, 1_000.0, 2_000.0])
    fills = [
        _fill(1, 10.0, 10.0),  # $100 traded
        _fill(1, 5.0, 20.0, side=Side.SELL),  # $100 traded, same event
        _fill(2, 10.0, 50.0),  # $500 traded
    ]
    assert per_event_turnover(fills, curve) == {
        1: pytest.approx(0.2),  # 200 / 1000
        2: pytest.approx(0.25),  # 500 / 2000
    }


def test_per_event_turnover_empty_and_bad_equity() -> None:
    assert per_event_turnover([], _curve([1_000.0])) == {}
    assert per_event_turnover([_fill(0, 1.0, 10.0)], _curve([0.0])) == {0: 0.0}


def test_annualized_turnover_scales_traded_value_per_year() -> None:
    # Exactly one year of curve at constant equity 1000; $2000 traded
    # -> 200% of equity per year.
    curve = _curve([1_000.0] * 367)  # 366 days apart = 2024 is a leap year
    fills = [_fill(1, 100.0, 10.0), _fill(50, 100.0, 10.0)]
    assert annualized_turnover(fills, curve) == pytest.approx(2.0, rel=0.01)


def test_annualized_turnover_degenerate_inputs() -> None:
    assert annualized_turnover([], []) == 0.0
    assert annualized_turnover([_fill(0, 1.0, 10.0)], _curve([1_000.0])) == 0.0
