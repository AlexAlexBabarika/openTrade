"""Turnover: the trading drag of a portfolio run.

Computed purely from fills and the equity curve — no engine bookkeeping.
Turnover here is gross: every fill contributes its absolute traded notional.
``per_event_turnover`` gives the per-rebalance distribution (traded value as
a fraction of that event's equity); ``annualized_turnover`` is the headline
gross-traded-value-per-year over average equity.
"""

from __future__ import annotations

from backend.backtesting.multi.book import PortfolioEquityPoint
from backend.backtesting.types import Fill

_SECONDS_PER_YEAR = 365.25 * 24 * 3600


def per_event_turnover(
    fills: list[Fill], equity_curve: list[PortfolioEquityPoint]
) -> dict[int, float]:
    """Traded value as a fraction of equity, per event index that traded."""
    traded: dict[int, float] = {}
    for fill in fills:
        traded[fill.fill_index] = traded.get(fill.fill_index, 0.0) + abs(
            fill.quantity * fill.price
        )
    out: dict[int, float] = {}
    for index in sorted(traded):
        equity = equity_curve[index].equity
        out[index] = traded[index] / equity if equity > 0.0 else 0.0
    return out


def annualized_turnover(
    fills: list[Fill], equity_curve: list[PortfolioEquityPoint]
) -> float:
    """Gross traded value per year as a multiple of average equity."""
    if len(equity_curve) < 2:
        return 0.0
    years = (
        equity_curve[-1].time - equity_curve[0].time
    ).total_seconds() / _SECONDS_PER_YEAR
    average_equity = sum(p.equity for p in equity_curve) / len(equity_curve)
    if years <= 0.0 or average_equity <= 0.0:
        return 0.0
    total_traded = sum(abs(f.quantity * f.price) for f in fills)
    return (total_traded / average_equity) / years
