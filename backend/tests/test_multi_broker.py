"""
The multi-symbol broker fills symbol-stamped orders against that symbol's bar
in each consumed MULTI_BAR event. Timing matches the single-symbol broker —
an order submitted at event t is eligible from event t+1 — and an order whose
symbol has no bar in an event (a data gap) keeps resting, so gaps never warp
fill timing across symbols.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.backtesting.costs import Costs, PerShareCommission
from backend.backtesting.errors import EngineError
from backend.backtesting.multi.broker import MultiBroker
from backend.backtesting.multi.timeline import MultiBarEvent
from backend.backtesting.types import Bar, Order, OrderType, Side


def _bar(close: float, day: int) -> Bar:
    t = datetime(2024, 1, day, tzinfo=timezone.utc)
    return Bar(
        time=t, open=close, high=close + 1, low=close - 1, close=close, volume=1000.0
    )


def _event(day: int, closes: dict[str, float]) -> MultiBarEvent:
    return MultiBarEvent(
        time=datetime(2024, 1, day, tzinfo=timezone.utc),
        bars={s: _bar(c, day) for s, c in sorted(closes.items())},
    )


def test_orders_require_a_symbol() -> None:
    broker = MultiBroker()
    with pytest.raises(EngineError):
        broker.submit(Order(side=Side.BUY, quantity=1.0), event_index=0)


def test_ids_are_global_across_symbols() -> None:
    broker = MultiBroker()
    a = broker.submit(Order(side=Side.BUY, quantity=1.0, symbol="AAPL"), event_index=0)
    b = broker.submit(Order(side=Side.BUY, quantity=1.0, symbol="MSFT"), event_index=0)
    assert (a.id, b.id) == (0, 1)


def test_fill_uses_the_orders_own_symbols_bar() -> None:
    broker = MultiBroker()
    broker.submit(Order(side=Side.BUY, quantity=2.0, symbol="MSFT"), event_index=0)
    fills = broker.process_event(_event(2, {"AAPL": 10.0, "MSFT": 20.0}), 1)
    assert len(fills) == 1
    assert fills[0].symbol == "MSFT"
    assert fills[0].price == 20.0  # MSFT's open, not AAPL's


def test_not_eligible_until_the_next_event() -> None:
    broker = MultiBroker()
    broker.submit(Order(side=Side.BUY, quantity=1.0, symbol="AAPL"), event_index=0)
    assert broker.process_event(_event(1, {"AAPL": 10.0}), 0) == []
    assert len(broker.process_event(_event(2, {"AAPL": 11.0}), 1)) == 1


def test_gap_in_the_symbols_data_keeps_the_order_resting() -> None:
    broker = MultiBroker()
    broker.submit(Order(side=Side.BUY, quantity=1.0, symbol="MSFT"), event_index=0)
    assert broker.process_event(_event(2, {"AAPL": 10.0}), 1) == []  # MSFT absent
    fills = broker.process_event(_event(3, {"AAPL": 10.0, "MSFT": 21.0}), 2)
    assert len(fills) == 1
    assert fills[0].fill_index == 2


def test_limit_order_rests_until_its_symbols_open_satisfies_it() -> None:
    broker = MultiBroker()
    broker.submit(
        Order(
            side=Side.BUY, quantity=1.0, symbol="AAPL", type=OrderType.LIMIT, limit=9.0
        ),
        event_index=0,
    )
    assert broker.process_event(_event(2, {"AAPL": 10.0}), 1) == []
    fills = broker.process_event(_event(3, {"AAPL": 8.0}), 2)
    assert len(fills) == 1
    assert fills[0].price == 8.0


def test_costs_are_applied_per_fill() -> None:
    costs = Costs(
        slippage=Costs.frictionless().slippage,
        spread=Costs.frictionless().spread,
        commission=PerShareCommission(0.5),
    )
    broker = MultiBroker(costs=costs)
    broker.submit(Order(side=Side.BUY, quantity=4.0, symbol="AAPL"), event_index=0)
    fills = broker.process_event(_event(2, {"AAPL": 10.0}), 1)
    assert fills[0].commission == 2.0


def test_fills_accumulate_in_deterministic_submission_order() -> None:
    broker = MultiBroker()
    broker.submit(Order(side=Side.BUY, quantity=1.0, symbol="MSFT"), event_index=0)
    broker.submit(Order(side=Side.BUY, quantity=1.0, symbol="AAPL"), event_index=0)
    fills = broker.process_event(_event(2, {"AAPL": 10.0, "MSFT": 20.0}), 1)
    assert [f.symbol for f in fills] == ["MSFT", "AAPL"]
    assert broker.fills == fills
