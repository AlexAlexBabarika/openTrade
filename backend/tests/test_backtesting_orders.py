"""
Orders submitted while processing bar t are only eligible to fill from bar t+1
onward (the t -> t+1 invariant that keeps fills free of look-ahead). The Broker
evaluates each resting order against the next bar's open (close for MOC) and
records the submission and fill bar indices plus a fill reason. Cost models
(slippage/commission/spread) and position accounting are later tasks.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.backtesting.context import BarSeries, Context
from backend.backtesting.errors import EngineError
from backend.backtesting.orders import Broker
from backend.backtesting.types import Bar, OrderType, Side


def _bar(
    o: float, c: float, *, i: int = 0, h: float | None = None, low: float | None = None
) -> Bar:
    return Bar(
        time=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
        open=o,
        high=h if h is not None else max(o, c) + 1,
        low=low if low is not None else min(o, c) - 1,
        close=c,
        volume=1000.0,
    )


def _market(side: Side = Side.BUY, qty: float = 10.0):
    return dict(side=side, quantity=qty, type=OrderType.MARKET)


# --- fill timing -----------------------------------------------------------


def test_market_order_fills_at_next_bar_open() -> None:
    broker = Broker()
    broker.submit_order(**_market(), bar_index=0)
    assert broker.process_bar(_bar(o=20.0, c=21.0, i=1), bar_index=1)[0].price == 20.0


def test_order_does_not_fill_on_its_submission_bar() -> None:
    broker = Broker()
    broker.submit_order(**_market(), bar_index=0)
    assert broker.process_bar(_bar(o=20.0, c=21.0, i=0), bar_index=0) == []


def test_fill_records_indices_quantity_side_and_reason() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.SELL, quantity=7.0, type=OrderType.MARKET, bar_index=2
    )
    fill = broker.process_bar(_bar(o=20.0, c=21.0, i=3), bar_index=3)[0]
    assert fill.submitted_index == 2
    assert fill.fill_index == 3
    assert fill.quantity == 7.0
    assert fill.side == Side.SELL
    assert fill.reason == "market"


# --- limit -----------------------------------------------------------------


def test_limit_buy_fills_when_open_at_or_below_limit() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.BUY, quantity=1.0, type=OrderType.LIMIT, limit=20.0, bar_index=0
    )
    assert broker.process_bar(_bar(o=19.5, c=21.0, i=1), bar_index=1)[0].price == 19.5


def test_limit_buy_rests_when_open_above_limit() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.BUY, quantity=1.0, type=OrderType.LIMIT, limit=20.0, bar_index=0
    )
    assert broker.process_bar(_bar(o=20.5, c=21.0, i=1), bar_index=1) == []


# --- stop ------------------------------------------------------------------


def test_stop_buy_fills_when_open_at_or_above_stop() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.BUY, quantity=1.0, type=OrderType.STOP, stop=25.0, bar_index=0
    )
    assert broker.process_bar(_bar(o=25.0, c=24.0, i=1), bar_index=1)[0].price == 25.0


def test_stop_sell_fills_when_open_at_or_below_stop() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.SELL, quantity=1.0, type=OrderType.STOP, stop=15.0, bar_index=0
    )
    assert broker.process_bar(_bar(o=14.0, c=13.0, i=1), bar_index=1)[0].price == 14.0


# --- stop-limit / moc / moo ------------------------------------------------


def test_stop_limit_stays_triggered_after_the_stop_is_hit() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.BUY,
        quantity=1.0,
        type=OrderType.STOP_LIMIT,
        stop=25.0,
        limit=26.0,
        bar_index=0,
    )
    # bar1: stop hit (27 >= 25) but above the limit -> no fill, now triggered.
    assert broker.process_bar(_bar(o=27.0, c=27.0, i=1), bar_index=1) == []
    # bar2: 24 is below the stop, but the order already triggered and 24 <= limit
    # -> it is now a resting limit and fills at 24 (it must not re-arm the stop).
    assert broker.process_bar(_bar(o=24.0, c=24.0, i=2), bar_index=2)[0].price == 24.0


def test_stop_limit_buy_fills_only_when_triggered_and_within_limit() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.BUY,
        quantity=1.0,
        type=OrderType.STOP_LIMIT,
        stop=25.0,
        limit=26.0,
        bar_index=0,
    )
    # open above stop (triggered) but above limit too -> no fill
    assert broker.process_bar(_bar(o=27.0, c=27.0, i=1), bar_index=1) == []
    # next bar opens triggered and within limit -> fill at open
    assert broker.process_bar(_bar(o=25.5, c=26.0, i=2), bar_index=2)[0].price == 25.5


def test_moc_fills_at_close_moo_fills_at_open() -> None:
    broker = Broker()
    broker.submit_order(side=Side.BUY, quantity=1.0, type=OrderType.MOC, bar_index=0)
    broker.submit_order(side=Side.BUY, quantity=1.0, type=OrderType.MOO, bar_index=0)
    fills = broker.process_bar(_bar(o=20.0, c=21.0, i=1), bar_index=1)
    by_reason = {f.reason: f.price for f in fills}
    assert by_reason["moc"] == 21.0
    assert by_reason["moo"] == 20.0


# --- resting persistence ---------------------------------------------------


def test_resting_order_persists_until_its_condition_is_met() -> None:
    broker = Broker()
    broker.submit_order(
        side=Side.BUY, quantity=1.0, type=OrderType.LIMIT, limit=20.0, bar_index=0
    )
    assert broker.process_bar(_bar(o=22.0, c=22.0, i=1), bar_index=1) == []
    assert broker.process_bar(_bar(o=21.0, c=21.0, i=2), bar_index=2) == []
    assert broker.process_bar(_bar(o=19.0, c=19.0, i=3), bar_index=3)[0].price == 19.0


# --- ctx.buy / ctx.sell ----------------------------------------------------


def _ctx_with_broker(bars: list[Bar]) -> tuple[Context, BarSeries, Broker]:
    series = BarSeries(bars)
    broker = Broker()
    return Context(series, broker=broker), series, broker


def test_ctx_buy_submits_order_that_fills_on_the_next_bar() -> None:
    bars = [_bar(o=10.0, c=10.0, i=0), _bar(o=12.0, c=13.0, i=1)]
    ctx, series, broker = _ctx_with_broker(bars)
    series.advance()  # reveal bar 0; current index 0
    ctx.buy(5.0)
    series.advance()  # reveal bar 1; current index 1
    fills = broker.process_bar(bars[1], bar_index=1)
    assert len(fills) == 1
    assert fills[0].side == Side.BUY
    assert fills[0].quantity == 5.0
    assert fills[0].price == 12.0


def test_ctx_sell_creates_a_sell_order() -> None:
    bars = [_bar(o=10.0, c=10.0, i=0), _bar(o=12.0, c=13.0, i=1)]
    ctx, series, broker = _ctx_with_broker(bars)
    series.advance()
    order = ctx.sell(3.0)
    assert order.side == Side.SELL
    assert order.submitted_index == 0


def test_ctx_buy_without_a_broker_raises() -> None:
    ctx = Context(BarSeries([_bar(o=10.0, c=10.0)]))
    with pytest.raises(EngineError):
        ctx.buy(1.0)
