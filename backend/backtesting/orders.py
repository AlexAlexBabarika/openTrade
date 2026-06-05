"""The fill engine.

The Broker holds resting orders and, as each bar is processed, fills those
eligible against that bar (close-to-close: evaluate the trigger on the bar's
open, MOC on its close). An order submitted while processing bar t is eligible
only from bar t+1 onward, which is what makes fills free of look-ahead.

Intrabar high/low crossing (a stop/limit that the open didn't reach but the
bar's range did) is a later task; here a resting order fills only if the open
itself satisfies it.
"""

from __future__ import annotations

from backend.backtesting.costs import Costs
from backend.backtesting.types import Bar, Fill, Order, OrderType, Side


class Broker:
    def __init__(self, costs: Costs | None = None) -> None:
        self._resting: list[Order] = []
        self.orders: list[Order] = []
        self.fills: list[Fill] = []
        self._next_id = 0
        self._costs = costs if costs is not None else Costs.frictionless()

    def submit(self, order: Order, *, bar_index: int) -> Order:
        """Register an order, stamping it with an id and its submission bar."""
        order.id = self._next_id
        self._next_id += 1
        order.submitted_index = bar_index
        self._resting.append(order)
        self.orders.append(order)
        return order

    def submit_order(
        self,
        *,
        side: Side,
        quantity: float,
        type: OrderType = OrderType.MARKET,
        limit: float | None = None,
        stop: float | None = None,
        bar_index: int,
    ) -> Order:
        return self.submit(
            Order(side=side, quantity=quantity, type=type, limit=limit, stop=stop),
            bar_index=bar_index,
        )

    def process_bar(self, bar: Bar, bar_index: int) -> list[Fill]:
        """Fill every eligible resting order against ``bar``; return new fills.

        Orders are evaluated in submission order so output is deterministic.
        """
        fills: list[Fill] = []
        still_resting: list[Order] = []
        for order in self._resting:
            assert order.submitted_index is not None and order.id is not None
            if order.submitted_index >= bar_index:
                still_resting.append(order)  # not eligible until the next bar
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
                    fill_index=bar_index,
                    reason=order.type.value,
                )
            )
        self._resting = still_resting
        self.fills.extend(fills)
        return fills


def _fill_price(order: Order, bar: Bar) -> float | None:
    """Close-to-close fill price for an order against ``bar``, or None if it rests."""
    o, c = bar.open, bar.close
    side, t = order.side, order.type

    if t in (OrderType.MARKET, OrderType.MOO):
        return o
    if t == OrderType.MOC:
        return c
    if t == OrderType.LIMIT:
        assert order.limit is not None
        if side == Side.BUY and o <= order.limit:
            return o
        if side == Side.SELL and o >= order.limit:
            return o
        return None
    if t == OrderType.STOP:
        assert order.stop is not None
        if side == Side.BUY and o >= order.stop:
            return o
        if side == Side.SELL and o <= order.stop:
            return o
        return None
    if t == OrderType.STOP_LIMIT:
        assert order.stop is not None and order.limit is not None
        if not order.triggered:
            stop_hit = (side == Side.BUY and o >= order.stop) or (
                side == Side.SELL and o <= order.stop
            )
            if not stop_hit:
                return None
            # The stop is consumed; the order is now a plain resting limit.
            order.triggered = True
        if side == Side.BUY and o <= order.limit:
            return o
        if side == Side.SELL and o >= order.limit:
            return o
        return None
    return None
