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
import uuid
from datetime import datetime, timezone

import polars as pl

from backend.backtesting.context import BarSeries, Context
from backend.backtesting.costs import Costs
from backend.backtesting.loop import EventLoop, bar_events_from_frame
from backend.backtesting.metrics import compute_metrics
from backend.backtesting.orders import Broker
from backend.backtesting.portfolio import Portfolio
from backend.backtesting.strategy import Strategy
from backend.backtesting.trades import match_trades
from backend.backtesting.types import BacktestResult, EquityPoint, RunMeta


def run_backtest(
    *,
    frame: pl.DataFrame,
    strategy: Strategy,
    starting_cash: float,
    costs: Costs | None = None,
    seed: int = 0,
    strategy_id: str | None = None,
    params: dict | None = None,
    data_version: str | None = None,
) -> BacktestResult:
    """Replay ``frame`` against ``strategy`` and return the full canonical record.

    ``costs`` defaults to the conservative ``Costs.default()`` — frictionless
    results require passing ``Costs.frictionless()`` explicitly. ``strategy_id``,
    ``params``, and ``data_version`` are recorded in ``meta`` for provenance.
    """
    if costs is None:
        costs = Costs.default()

    started_at = datetime.now(timezone.utc)

    events = sorted(bar_events_from_frame(frame), key=lambda e: e.time)
    loop = EventLoop(events)
    bars = [ev.bar for ev in events]
    series = BarSeries(bars)
    broker = Broker(costs=costs)
    portfolio = Portfolio(starting_cash=starting_cash)
    ctx = Context(
        series,
        broker=broker,
        portfolio=portfolio,
        rng=random.Random(seed),
        params=params,
    )

    for index, event in enumerate(loop):
        series.advance()
        for fill in broker.process_bar(event.bar, index):
            portfolio.apply_fill(fill)
        strategy.on_bar(ctx)
        portfolio.mark_to_market(event.bar.time, event.bar.close)

    trades = match_trades(broker.fills, [b.time for b in bars])
    metrics = compute_metrics(portfolio.equity_curve, trades, bars)

    return BacktestResult(
        meta=RunMeta(
            run_id=uuid.uuid4().hex,
            seed=seed,
            starting_cash=starting_cash,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            strategy_id=strategy_id,
            params=params,
            data_version=data_version,
        ),
        bars=bars,
        orders=broker.orders,
        fills=broker.fills,
        equity_curve=portfolio.equity_curve,
        trades=trades,
        metrics=metrics,
    )


def equity_curve_hash(curve: list[EquityPoint]) -> str:
    """A stable SHA-256 over the equity curve for golden-value regression."""
    h = hashlib.sha256()
    for point in curve:
        h.update(f"{point.time.isoformat()}|{point.equity!r}\n".encode())
    return h.hexdigest()
