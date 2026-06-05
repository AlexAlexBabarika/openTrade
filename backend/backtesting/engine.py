"""The run loop and determinism utilities.

Drives the simulation bar by bar. Per bar the engine:
  1. reveals the bar (advances the clock),
  2. fills orders resting from earlier bars and applies them to the portfolio,
  3. calls the strategy, which may submit orders (eligible from the next bar),
  4. marks the portfolio to the bar's close, recording an equity point.

This ordering is what enforces the t -> t+1 fill timing. Determinism: the only
stochastic input is the seeded ``ctx.random``; iteration order over orders and
the equity curve is list-stable, with no dependence on dict/set/hash ordering,
so the same inputs yield a byte-identical equity curve.
"""

from __future__ import annotations

import hashlib
import random

import polars as pl

from backend.backtesting.context import BarSeries, Context
from backend.backtesting.costs import Costs
from backend.backtesting.loop import EventLoop, bar_events_from_frame
from backend.backtesting.orders import Broker
from backend.backtesting.portfolio import Portfolio
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import BacktestResult, EquityPoint


def run_backtest(
    *,
    frame: pl.DataFrame,
    strategy: Strategy,
    starting_cash: float,
    costs: Costs | None = None,
    seed: int = 0,
) -> BacktestResult:
    """Replay ``frame`` against ``strategy`` and return the full record.

    ``costs`` defaults to the conservative ``Costs.default()`` — frictionless
    results require passing ``Costs.frictionless()`` explicitly.
    """
    if costs is None:
        costs = Costs.default()

    events = sorted(bar_events_from_frame(frame), key=lambda e: e.time)
    loop = EventLoop(events)
    series = BarSeries([ev.bar for ev in events])
    broker = Broker(costs=costs)
    portfolio = Portfolio(starting_cash=starting_cash)
    ctx = Context(series, broker=broker, portfolio=portfolio, rng=random.Random(seed))

    for index, event in enumerate(loop):
        series.advance()
        for fill in broker.process_bar(event.bar, index):
            portfolio.apply_fill(fill)
        strategy.on_bar(ctx)
        portfolio.mark_to_market(event.bar.time, event.bar.close)

    return BacktestResult(
        orders=broker.orders,
        fills=broker.fills,
        equity_curve=portfolio.equity_curve,
    )


def equity_curve_hash(curve: list[EquityPoint]) -> str:
    """A stable SHA-256 over the equity curve for golden-value regression."""
    h = hashlib.sha256()
    for point in curve:
        h.update(f"{point.time.isoformat()}|{point.equity!r}\n".encode())
    return h.hexdigest()
