"""The portfolio run loop.

Per consumed MULTI_BAR event the engine:
  1. reveals the event's bars (advancing each present symbol's cursor) and
     refreshes the last-known close marks,
  2. fills eligible resting orders and applies them to the book,
  3. applies universe membership: resting orders of symbols that left are
     cancelled, and open positions in them are flattened via a market order
     submitted through the normal path — so the exit fills next event with
     realistic costs and appears in the trade log,
  4. calls the strategy with the universe-gated context,
  5. marks the book to the latest known closes, recording an equity point.

If a departing symbol has no further bars in the data, its flatten order can
never fill and the position stays marked at its last known close.

Determinism mirrors the single-symbol engine: symbols are iterated in sorted
order everywhere and the only stochastic input is the seeded ``ctx.random``.
"""

from __future__ import annotations

import dataclasses
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import polars as pl

from backend.backtesting.costs import Costs
from backend.backtesting.errors import UniverseError
from backend.backtesting.multi.book import PortfolioBook, PortfolioEquityPoint
from backend.backtesting.multi.broker import MultiBroker
from backend.backtesting.multi.context import PortfolioContext
from backend.backtesting.multi.timeline import (
    MultiBarEvent,
    MultiBarSeries,
    events_from_frames,
)
from backend.backtesting.multi.universe import Universe
from backend.backtesting.strategy import Strategy
from backend.backtesting.trades import match_trades
from backend.backtesting.types import Fill, Order, RunMeta, Side, Trade


@dataclass(frozen=True, slots=True)
class PortfolioBacktestResult:
    """The canonical record of a portfolio run (metrics arrive in a later task)."""

    meta: RunMeta
    events: list[MultiBarEvent]
    orders: list[Order]
    fills: list[Fill]
    equity_curve: list[PortfolioEquityPoint]
    trades: list[Trade]


def run_portfolio_backtest(
    *,
    frames: dict[str, pl.DataFrame],
    strategy: Strategy,
    starting_cash: float,
    universe: Universe | None = None,
    costs: Costs | None = None,
    seed: int = 0,
    strategy_id: str | None = None,
    params: dict | None = None,
    data_version: str | None = None,
) -> PortfolioBacktestResult:
    """Replay ``frames`` (one OHLCV frame per symbol) against ``strategy``.

    ``universe`` defaults to a static universe of all frame symbols; every
    universe symbol must have a frame. ``costs`` defaults to the conservative
    ``Costs.default()``.
    """
    if costs is None:
        costs = Costs.default()
    if universe is None:
        universe = Universe.static(frames)
    missing = [s for s in universe.symbols if s not in frames]
    if missing:
        raise UniverseError(f"universe symbols without data: {missing}")

    started_at = datetime.now(timezone.utc)

    events = events_from_frames(frames)
    series = MultiBarSeries(events)
    broker = MultiBroker(costs=costs)
    book = PortfolioBook(starting_cash=starting_cash)
    marks: dict[str, float] = {}
    ctx = PortfolioContext(
        series,
        broker=broker,
        book=book,
        marks=marks,
        rng=random.Random(seed),
        params=params,
    )

    prev_active: set[str] = set()
    for index, event in enumerate(events):
        series.advance(event)
        for symbol, bar in event.bars.items():
            marks[symbol] = bar.close
        for fill in broker.process_event(event, index):
            book.apply_fill(fill)

        active = universe.active(event.time)
        ctx._set_event(event, index, active)
        for symbol in sorted(prev_active.difference(active)):
            broker.cancel_resting(symbol)
            quantity = book.position(symbol).quantity
            if quantity != 0.0:
                side = Side.SELL if quantity > 0 else Side.BUY
                broker.submit(
                    Order(side=side, quantity=abs(quantity), symbol=symbol),
                    event_index=index,
                )
        prev_active = set(active)

        strategy.on_bar(ctx)
        book.mark_to_market(event.time, marks)

    event_times = [e.time for e in events]
    trades: list[Trade] = []
    for symbol in sorted({f.symbol for f in broker.fills if f.symbol is not None}):
        symbol_fills = [f for f in broker.fills if f.symbol == symbol]
        trades.extend(
            dataclasses.replace(t, symbol=symbol)
            for t in match_trades(symbol_fills, event_times)
        )
    trades.sort(key=lambda t: (t.exit_index, t.symbol or ""))

    return PortfolioBacktestResult(
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
        events=events,
        orders=broker.orders,
        fills=broker.fills,
        equity_curve=book.equity_curve,
        trades=trades,
    )
