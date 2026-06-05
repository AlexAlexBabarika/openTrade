"""Portfolio accounting and the equity curve.

Tracks cash and a single signed position with an average entry price, realizing
PnL whenever a fill reduces or closes the open quantity. Equity is marked to a
bar's close: cash plus the marked value of the position. The fill price already
includes slippage and half-spread (see costs); commission is a separate cash
charge.
"""

from __future__ import annotations

from datetime import datetime

from backend.backtesting.types import EquityPoint, Fill, Position, Side


# Quantities below this are treated as flat, so float dust from fractional-share
# arithmetic (e.g. 0.1 + 0.1 + 0.1 - 0.3) doesn't leave a phantom position.
_QTY_EPS = 1e-9


def _sign(x: float) -> float:
    if x > _QTY_EPS:
        return 1.0
    if x < -_QTY_EPS:
        return -1.0
    return 0.0


class Portfolio:
    def __init__(self, starting_cash: float) -> None:
        self._cash = starting_cash
        self._position = Position()
        self._realized_pnl = 0.0
        self.equity_curve: list[EquityPoint] = []

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def position(self) -> Position:
        return self._position

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    def apply_fill(self, fill: Fill) -> None:
        delta = fill.quantity if fill.side == Side.BUY else -fill.quantity
        price = fill.price

        # Cash: a buy spends, a sell receives; commission is always a cost.
        self._cash -= delta * price + fill.commission

        old_qty = self._position.quantity
        old_avg = self._position.avg_price
        new_qty = old_qty + delta
        if abs(new_qty) < _QTY_EPS:
            new_qty = 0.0  # snap float dust to exactly flat

        if _sign(old_qty) == 0.0 or _sign(old_qty) == _sign(delta):
            # Opening or increasing in the same direction: weighted average.
            new_avg = (old_qty * old_avg + delta * price) / new_qty
            self._position = Position(quantity=new_qty, avg_price=new_avg)
        else:
            # Reducing, closing, or flipping: realize PnL on the closed amount.
            closed = min(abs(delta), abs(old_qty))
            self._realized_pnl += (price - old_avg) * closed * _sign(old_qty)
            if abs(delta) <= abs(old_qty):
                avg = 0.0 if new_qty == 0.0 else old_avg
                self._position = Position(quantity=new_qty, avg_price=avg)
            else:
                # Flipped past flat: remainder opens a new position at this price.
                self._position = Position(quantity=new_qty, avg_price=price)

    def unrealized_pnl(self, mark_price: float) -> float:
        return self._position.quantity * (mark_price - self._position.avg_price)

    def equity(self, mark_price: float) -> float:
        return self._cash + self._position.quantity * mark_price

    def mark_to_market(self, time: datetime, mark_price: float) -> EquityPoint:
        holdings = self._position.quantity * mark_price
        point = EquityPoint(
            time=time,
            equity=self._cash + holdings,
            cash=self._cash,
            holdings=holdings,
        )
        self.equity_curve.append(point)
        return point
