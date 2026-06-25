"""Portfolio accounting and the equity curve.

Cash, a signed position with an average entry price, realized PnL on closes, and
mark-to-market equity/unrealized PnL against the current bar's close. The
accounting must handle increasing, reducing, closing, and flipping a position,
long and short. ctx exposes position/cash/equity off the portfolio.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.backtesting.context import BarSeries, Context
from backend.backtesting.errors import EngineError
from backend.backtesting.portfolio import Portfolio
from backend.backtesting.types import Bar, Fill, Side


def _fill(side: Side, qty: float, price: float, *, commission: float = 0.0) -> Fill:
    return Fill(
        order_id=0,
        side=side,
        quantity=qty,
        price=price,
        reference_price=price,
        slippage=0.0,
        spread_cost=0.0,
        commission=commission,
        submitted_index=0,
        fill_index=1,
        reason="market",
    )


def _bar(c: float, *, i: int = 0) -> Bar:
    return Bar(
        time=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
        open=c,
        high=c + 1,
        low=c - 1,
        close=c,
        volume=1000.0,
    )


# --- cash & position -------------------------------------------------------


def test_starting_cash() -> None:
    assert Portfolio(starting_cash=1000.0).cash == 1000.0


def test_buy_reduces_cash_and_opens_long() -> None:
    p = Portfolio(starting_cash=1000.0)
    p.apply_fill(_fill(Side.BUY, 5.0, 100.0))
    assert p.cash == 500.0
    assert p.position.quantity == 5.0
    assert p.position.avg_price == 100.0


def test_commission_reduces_cash_further() -> None:
    p = Portfolio(starting_cash=1000.0)
    p.apply_fill(_fill(Side.BUY, 5.0, 100.0, commission=2.0))
    assert p.cash == 498.0


def test_increasing_long_updates_weighted_average_price() -> None:
    p = Portfolio(starting_cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, 10.0, 100.0))
    p.apply_fill(_fill(Side.BUY, 10.0, 120.0))
    assert p.position.quantity == 20.0
    assert p.position.avg_price == 110.0


def test_selling_a_long_realizes_pnl_and_keeps_average() -> None:
    p = Portfolio(starting_cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, 10.0, 100.0))
    p.apply_fill(_fill(Side.SELL, 4.0, 110.0))
    assert p.position.quantity == 6.0
    assert p.position.avg_price == 100.0
    assert p.realized_pnl == 40.0  # (110 - 100) * 4


def test_selling_more_than_long_flips_to_short() -> None:
    p = Portfolio(starting_cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, 10.0, 100.0))
    p.apply_fill(_fill(Side.SELL, 15.0, 110.0))
    assert p.position.quantity == -5.0
    assert p.position.avg_price == 110.0  # remainder opens short at fill price
    assert p.realized_pnl == 100.0  # closed 10 long at +10 each


def test_fractional_shares_net_to_exactly_flat() -> None:
    p = Portfolio(starting_cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, 0.1, 100.0))
    p.apply_fill(_fill(Side.BUY, 0.1, 100.0))
    p.apply_fill(_fill(Side.BUY, 0.1, 100.0))  # 0.30000000000000004 from float add
    p.apply_fill(_fill(Side.SELL, 0.3, 110.0))
    assert p.position.quantity == 0.0  # snapped flat, not a 1e-17 dust position
    assert p.position.avg_price == 0.0
    assert p.realized_pnl == pytest.approx(3.0)  # (110 - 100) * 0.3


def test_short_then_cover_below_entry_realizes_profit() -> None:
    p = Portfolio(starting_cash=10_000.0)
    p.apply_fill(_fill(Side.SELL, 10.0, 100.0))
    assert p.position.quantity == -10.0
    p.apply_fill(_fill(Side.BUY, 10.0, 90.0))
    assert p.position.quantity == 0.0
    assert p.realized_pnl == 100.0  # (100 - 90) * 10


# --- mark to market --------------------------------------------------------


def test_equity_is_cash_plus_marked_position() -> None:
    p = Portfolio(starting_cash=1000.0)
    p.apply_fill(_fill(Side.BUY, 5.0, 100.0))  # cash 500, qty 5
    assert p.equity(mark_price=120.0) == 1100.0  # 500 + 5 * 120


def test_unrealized_pnl_long_and_short() -> None:
    p = Portfolio(starting_cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, 10.0, 100.0))
    assert p.unrealized_pnl(mark_price=110.0) == 100.0
    q = Portfolio(starting_cash=10_000.0)
    q.apply_fill(_fill(Side.SELL, 10.0, 100.0))
    assert q.unrealized_pnl(mark_price=90.0) == 100.0


def test_mark_to_market_appends_an_equity_point() -> None:
    p = Portfolio(starting_cash=1000.0)
    p.apply_fill(_fill(Side.BUY, 5.0, 100.0))
    bar = _bar(120.0, i=1)
    point = p.mark_to_market(bar.time, bar.close)
    assert point.equity == 1100.0
    assert point.time == bar.time
    assert p.equity_curve == [point]


# --- ctx integration -------------------------------------------------------


def test_ctx_position_cash_equity_reflect_the_portfolio() -> None:
    bars = [_bar(100.0, i=0), _bar(120.0, i=1)]
    series = BarSeries(bars)
    portfolio = Portfolio(starting_cash=1000.0)
    portfolio.apply_fill(_fill(Side.BUY, 5.0, 100.0))
    ctx = Context(series, portfolio=portfolio)
    series.advance()
    series.advance()  # current bar close = 120
    assert ctx.cash == 500.0
    assert ctx.position.quantity == 5.0
    assert ctx.equity == 1100.0  # 500 + 5 * 120


def test_ctx_position_without_portfolio_raises() -> None:
    ctx = Context(BarSeries([_bar(100.0)]))
    with pytest.raises(EngineError):
        _ = ctx.position
