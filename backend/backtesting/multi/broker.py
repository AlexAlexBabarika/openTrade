"""The multi-symbol fill engine.

Same fill semantics as the single-symbol ``Broker`` — an order submitted while
processing event t is eligible from event t+1, evaluated close-to-close via
the shared ``_fill_price`` rules and ``Costs`` models — but each order fills
against its own symbol's bar within the consumed MULTI_BAR event. An order
whose symbol has no bar in an event (a data gap) keeps resting. Order ids are
global across symbols and fills are evaluated in submission order, so output
is deterministic.
"""

from __future__ import annotations

from backend.backtesting.costs import Costs
from backend.backtesting.errors import EngineError
from backend.backtesting.multi.timeline import MultiBarEvent
from backend.backtesting.orders import _fill_price
from backend.backtesting.types import Fill, Order


class MultiBroker:
    def __init__(self, costs: Costs | None = None) -> None:
        self._resting: list[Order] = []
        self.orders: list[Order] = []
        self.fills: list[Fill] = []
        self._next_id = 0
        self._costs = costs if costs is not None else Costs.frictionless()

    def submit(self, order: Order, *, event_index: int) -> Order:
        """Register a symbol-stamped order, assigning a global id."""
        if not order.symbol:
            raise EngineError("multi-asset orders must carry a symbol")
        order.id = self._next_id
        self._next_id += 1
        order.submitted_index = event_index
        self._resting.append(order)
        self.orders.append(order)
        return order

    def process_event(self, event: MultiBarEvent, event_index: int) -> list[Fill]:
        """Fill every eligible resting order against its symbol's bar in
        ``event``; return the new fills in submission order."""
        fills: list[Fill] = []
        still_resting: list[Order] = []
        for order in self._resting:
            assert order.submitted_index is not None and order.id is not None
            bar = event.bars.get(order.symbol or "")
            if order.submitted_index >= event_index or bar is None:
                still_resting.append(order)
                continue
            reference_price = _fill_price(order, bar)
            if reference_price is None:
                still_resting.append(order)  # condition not met; keep resting
                continue
            price, slippage, spread_cost, commission = self._costs.apply(
                reference_price=reference_price,
                side=order.side,
                quantity=order.quantity,
                bar=bar,
            )
            fills.append(
                Fill(
                    order_id=order.id,
                    side=order.side,
                    quantity=order.quantity,
                    price=price,
                    reference_price=reference_price,
                    slippage=slippage,
                    spread_cost=spread_cost,
                    commission=commission,
                    submitted_index=order.submitted_index,
                    fill_index=event_index,
                    reason=order.type.value,
                    symbol=order.symbol,
                )
            )
        self._resting = still_resting
        self.fills.extend(fills)
        return fills
