"""Multi-asset portfolio accounting.

One shared cash balance, one signed position per symbol. Position and
realized-PnL math is delegated to a per-symbol single-symbol ``Portfolio``
opened with zero cash — its cash balance then equals that symbol's cumulative
trading cash flow, and total cash is starting cash plus the sum. This reuses
the verified single-symbol accounting (averaging, reduce/flip realization,
float-dust snapping) instead of duplicating it.

The equity curve points carry per-symbol weights so holdings panels and
weight-over-time heatmaps are pure readers of the curve.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.backtesting.portfolio import Portfolio
from backend.backtesting.types import Fill, Position


@dataclass(frozen=True, slots=True)
class PortfolioEquityPoint:
    """One sample of the portfolio equity curve.

    ``equity == cash + holdings``; ``holdings`` is the summed signed marked
    value of all open positions. ``weights`` maps each open symbol to its
    signed fraction of equity (empty when flat or equity is non-positive).
    """

    time: datetime
    equity: float
    cash: float
    holdings: float
    weights: dict[str, float]


class PortfolioBook:
    def __init__(self, starting_cash: float) -> None:
        self._starting_cash = starting_cash
        self._legs: dict[str, Portfolio] = {}
        self.equity_curve: list[PortfolioEquityPoint] = []

    def _leg(self, symbol: str) -> Portfolio:
        if symbol not in self._legs:
            self._legs[symbol] = Portfolio(starting_cash=0.0)
        return self._legs[symbol]

    @property
    def cash(self) -> float:
        return self._starting_cash + sum(
            leg.cash for _, leg in sorted(self._legs.items())
        )

    def position(self, symbol: str) -> Position:
        leg = self._legs.get(symbol)
        return leg.position if leg is not None else Position()

    @property
    def open_positions(self) -> dict[str, Position]:
        """Non-flat positions keyed by symbol, in sorted symbol order."""
        return {
            symbol: leg.position
            for symbol, leg in sorted(self._legs.items())
            if leg.position.quantity != 0.0
        }

    def realized_pnl(self, symbol: str) -> float:
        leg = self._legs.get(symbol)
        return leg.realized_pnl if leg is not None else 0.0

    @property
    def total_realized_pnl(self) -> float:
        return sum(leg.realized_pnl for _, leg in sorted(self._legs.items()))

    def apply_fill(self, fill: Fill) -> None:
        if fill.symbol is None:
            raise ValueError("portfolio book requires symbol-stamped fills")
        self._leg(fill.symbol).apply_fill(fill)

    def holdings(self, marks: dict[str, float]) -> float:
        """Summed signed marked value of all open positions."""
        return sum(
            leg.position.quantity * marks[symbol]
            for symbol, leg in sorted(self._legs.items())
            if leg.position.quantity != 0.0
        )

    def equity(self, marks: dict[str, float]) -> float:
        return self.cash + self.holdings(marks)

    def weights(self, marks: dict[str, float]) -> dict[str, float]:
        """Signed weight of each open position as a fraction of equity."""
        equity = self.equity(marks)
        if equity <= 0.0:
            return {}
        return {
            symbol: position.quantity * marks[symbol] / equity
            for symbol, position in self.open_positions.items()
        }

    def mark_to_market(
        self, time: datetime, marks: dict[str, float]
    ) -> PortfolioEquityPoint:
        """Record an equity point marked to ``marks`` (one price per symbol).

        ``marks`` must price every open symbol; symbols without a bar at this
        time should be marked at their last known close by the caller.
        """
        cash = self.cash
        holdings = self.holdings(marks)
        equity = cash + holdings
        point = PortfolioEquityPoint(
            time=time,
            equity=equity,
            cash=cash,
            holdings=holdings,
            weights=self.weights(marks),
        )
        self.equity_curve.append(point)
        return point
