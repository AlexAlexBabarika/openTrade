"""Fills -> matched round-trip trades.

A trade opens when the signed position leaves flat and closes when it returns to
flat. Scale-ins/outs aggregate into one trade; a fill that crosses through flat
is split into a closing leg and a new opening leg. P&L is computed from effective
fill prices and commissions so it reconciles with the portfolio's realized P&L.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.backtesting.trades import match_trades
from backend.backtesting.types import Fill, Side


def _times(n: int) -> list[datetime]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [start + timedelta(days=i) for i in range(n)]


def _fill(
    *,
    side: Side,
    quantity: float,
    price: float,
    fill_index: int,
    commission: float = 0.0,
) -> Fill:
    return Fill(
        order_id=0,
        side=side,
        quantity=quantity,
        price=price,
        reference_price=price,
        slippage=0.0,
        spread_cost=0.0,
        commission=commission,
        submitted_index=fill_index - 1,
        fill_index=fill_index,
        reason="market",
    )


def test_no_fills_yields_no_trades():
    assert match_trades([], _times(5)) == []


def test_open_without_close_is_not_a_trade():
    # Bought but never sold: position never returns to flat.
    fills = [_fill(side=Side.BUY, quantity=10.0, price=100.0, fill_index=1)]
    assert match_trades(fills, _times(5)) == []


def test_simple_long_round_trip():
    fills = [
        _fill(side=Side.BUY, quantity=10.0, price=100.0, fill_index=1),
        _fill(side=Side.SELL, quantity=10.0, price=110.0, fill_index=4),
    ]
    (trade,) = match_trades(fills, _times(6))

    assert trade.direction == Side.BUY
    assert trade.quantity == 10.0
    assert trade.entry_index == 1
    assert trade.exit_index == 4
    assert trade.entry_price == 100.0
    assert trade.exit_price == 110.0
    assert trade.pnl == 100.0  # (110 - 100) * 10
    assert trade.pnl_pct == 0.1  # 100 / 1000
    assert trade.bars_held == 3  # 4 - 1
    assert trade.entry_time == _times(6)[1]
    assert trade.exit_time == _times(6)[4]


def test_commissions_reduce_pnl():
    fills = [
        _fill(side=Side.BUY, quantity=10.0, price=100.0, fill_index=1, commission=2.0),
        _fill(side=Side.SELL, quantity=10.0, price=110.0, fill_index=2, commission=3.0),
    ]
    (trade,) = match_trades(fills, _times(4))
    assert trade.pnl == 95.0  # 100 gross - 5 commissions


def test_short_round_trip():
    fills = [
        _fill(side=Side.SELL, quantity=5.0, price=100.0, fill_index=1),
        _fill(side=Side.BUY, quantity=5.0, price=90.0, fill_index=3),
    ]
    (trade,) = match_trades(fills, _times(5))
    assert trade.direction == Side.SELL
    assert trade.entry_price == 100.0
    assert trade.exit_price == 90.0
    assert trade.pnl == 50.0  # short: (100 - 90) * 5


def test_scale_in_then_full_exit_is_one_trade():
    fills = [
        _fill(side=Side.BUY, quantity=10.0, price=100.0, fill_index=1),
        _fill(side=Side.BUY, quantity=10.0, price=120.0, fill_index=2),
        _fill(side=Side.SELL, quantity=20.0, price=130.0, fill_index=5),
    ]
    (trade,) = match_trades(fills, _times(6))
    assert trade.quantity == 20.0
    assert trade.entry_price == 110.0  # (10*100 + 10*120) / 20
    assert trade.exit_price == 130.0
    assert trade.pnl == 400.0  # (130 - 110) * 20
    assert trade.bars_held == 4  # 5 - 1


def test_flip_through_flat_splits_into_two_trades():
    # Long 10, then sell 15: closes the long (10) and opens a short (5).
    fills = [
        _fill(side=Side.BUY, quantity=10.0, price=100.0, fill_index=1),
        _fill(side=Side.SELL, quantity=15.0, price=120.0, fill_index=3),
        _fill(side=Side.BUY, quantity=5.0, price=115.0, fill_index=6),
    ]
    long_trade, short_trade = match_trades(fills, _times(8))

    assert long_trade.direction == Side.BUY
    assert long_trade.quantity == 10.0
    assert long_trade.pnl == 200.0  # (120 - 100) * 10
    assert long_trade.exit_index == 3

    assert short_trade.direction == Side.SELL
    assert short_trade.quantity == 5.0
    assert short_trade.entry_index == 3  # opened by the flipping fill
    assert short_trade.exit_index == 6
    assert short_trade.pnl == 25.0  # short: (120 - 115) * 5


def test_scale_out_then_full_exit_is_one_trade():
    # Long 10, sell 5 (partial scale-out, still long 5), then sell 5 (now flat).
    fills = [
        _fill(side=Side.BUY, quantity=10.0, price=100.0, fill_index=1),
        _fill(side=Side.SELL, quantity=5.0, price=110.0, fill_index=3),
        _fill(side=Side.SELL, quantity=5.0, price=120.0, fill_index=5),
    ]
    (trade,) = match_trades(fills, _times(7))
    assert trade.quantity == 10.0
    assert trade.exit_price == 115.0  # weighted: (5*110 + 5*120) / 10
    assert trade.pnl == 150.0  # (115 - 100) * 10
    assert trade.bars_held == 4  # 5 - 1


def test_flip_splits_commission_between_trades():
    # Sell 15 against long 10: commission 9 splits 6 (closing 10/15) / 3 (opening 5/15).
    fills = [
        _fill(side=Side.BUY, quantity=10.0, price=100.0, fill_index=1, commission=0.0),
        _fill(side=Side.SELL, quantity=15.0, price=120.0, fill_index=3, commission=9.0),
        _fill(side=Side.BUY, quantity=5.0, price=115.0, fill_index=6, commission=0.0),
    ]
    long_trade, short_trade = match_trades(fills, _times(8))
    assert long_trade.pnl == 194.0  # 200 gross - 6 commission
    assert short_trade.pnl == 22.0  # 25 gross - 3 commission
