"""
target_weight / rebalance is the portfolio strategy's primary interface: the
strategy declares intended weights, the engine diffs them against the current
book and submits only the delta as market orders (which fill next bar through
the normal cost-paying path). Targets persist across bars so calling
rebalance() again corrects drift; a symbol leaving the universe clears its
target. min_trade_value skips dust trades to avoid fee bleed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from backend.backtesting.costs import Costs
from backend.backtesting.errors import UniverseError
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.universe import Membership, Universe
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import Side


def _t(day: int) -> datetime:
    return datetime(2024, 1, day, tzinfo=timezone.utc)


def _frame(closes: list[float], *, start_day: int = 1) -> pl.DataFrame:
    start = _t(start_day)
    ts = [start + timedelta(days=i) for i in range(len(closes))]
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000.0] * len(closes),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


def test_rebalance_from_cash_hits_target_weights() -> None:
    frames = {"AAPL": _frame([10.0] * 4), "MSFT": _frame([20.0] * 4)}

    class FiftyFifty(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("AAPL", 0.5)
                ctx.target_weight("MSFT", 0.5)
                orders = ctx.rebalance()
                assert [(o.symbol, o.side, o.quantity) for o in orders] == [
                    ("AAPL", Side.BUY, 50.0),
                    ("MSFT", Side.BUY, 25.0),
                ]

    result = run_portfolio_backtest(
        frames=frames,
        strategy=FiftyFifty(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    final = result.equity_curve[-1]
    assert final.weights == {"AAPL": 0.5, "MSFT": 0.5}
    assert final.cash == 0.0


def test_rebalance_submits_only_the_diff() -> None:
    frames = {"AAPL": _frame([10.0] * 6), "MSFT": _frame([20.0] * 6)}

    class Rotate(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("AAPL", 0.5)
                ctx.target_weight("MSFT", 0.5)
                ctx.rebalance()
            if ctx.time.day == 3:
                ctx.target_weight("AAPL", 1.0)
                ctx.target_weight("MSFT", 0.0)
                orders = ctx.rebalance()
                assert [(o.symbol, o.side, o.quantity) for o in orders] == [
                    ("AAPL", Side.BUY, 50.0),
                    ("MSFT", Side.SELL, 25.0),
                ]

    result = run_portfolio_backtest(
        frames=frames,
        strategy=Rotate(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    final = result.equity_curve[-1]
    assert final.weights == {"AAPL": 1.0}
    msft_trades = [t for t in result.trades if t.symbol == "MSFT"]
    assert len(msft_trades) == 1


def test_rebalance_with_no_drift_is_a_no_op() -> None:
    frames = {"AAPL": _frame([10.0] * 5)}

    class Steady(Strategy):
        def __init__(self) -> None:
            self.late_orders = []

        def on_bar(self, ctx) -> None:
            ctx.target_weight("AAPL", 0.5)
            orders = ctx.rebalance()
            if ctx.time.day >= 3:  # position established and prices flat
                self.late_orders.extend(orders)

    strategy = Steady()
    run_portfolio_backtest(
        frames=frames,
        strategy=strategy,
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    assert strategy.late_orders == []


def test_persistent_targets_correct_drift() -> None:
    # AAPL doubles on day 3; an untouched 50/50 target should sell AAPL
    # and buy MSFT when rebalance() is called again.
    frames = {
        "AAPL": _frame([10.0, 10.0, 20.0, 20.0, 20.0]),
        "MSFT": _frame([20.0] * 5),
    }

    class Drift(Strategy):
        def __init__(self) -> None:
            self.day3_orders = []

        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("AAPL", 0.5)
                ctx.target_weight("MSFT", 0.5)
            orders = ctx.rebalance()
            if ctx.time.day == 3:
                self.day3_orders = orders

    strategy = Drift()
    run_portfolio_backtest(
        frames=frames,
        strategy=strategy,
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    sides = {o.symbol: o.side for o in strategy.day3_orders}
    assert sides == {"AAPL": Side.SELL, "MSFT": Side.BUY}


def test_min_trade_value_skips_dust_trades() -> None:
    # Tiny drift: AAPL ticks from 10.00 to 10.01 on day 3 (~0.05% drift).
    frames = {
        "AAPL": _frame([10.0, 10.0, 10.01, 10.01]),
        "MSFT": _frame([20.0] * 4),
    }

    class Threshold(Strategy):
        def __init__(self) -> None:
            self.day3_orders = []

        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("AAPL", 0.5)
                ctx.target_weight("MSFT", 0.5)
                ctx.rebalance()
            if ctx.time.day == 3:
                self.day3_orders = ctx.rebalance(min_trade_value=10.0)

    strategy = Threshold()
    run_portfolio_backtest(
        frames=frames,
        strategy=strategy,
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    assert strategy.day3_orders == []


def test_short_target_weight_sells_short() -> None:
    frames = {"AAPL": _frame([10.0] * 4)}

    class ShortIt(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("AAPL", -0.3)
                orders = ctx.rebalance()
                assert [(o.side, o.quantity) for o in orders] == [(Side.SELL, 30.0)]

    result = run_portfolio_backtest(
        frames=frames,
        strategy=ShortIt(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    assert result.equity_curve[-1].weights == {"AAPL": -0.3}


def test_target_weight_on_inactive_symbol_raises() -> None:
    frames = {"AAPL": _frame([10.0] * 3), "MSFT": _frame([20.0] * 3)}
    far_future = datetime(2030, 1, 1, tzinfo=timezone.utc)
    universe = Universe([Membership("AAPL"), Membership("MSFT", start=far_future)])

    class Naughty(Strategy):
        def on_bar(self, ctx) -> None:
            with pytest.raises(UniverseError):
                ctx.target_weight("MSFT", 0.5)

    run_portfolio_backtest(
        frames=frames,
        strategy=Naughty(),
        starting_cash=1_000.0,
        universe=universe,
        costs=Costs.frictionless(),
    )


def test_departure_clears_the_target() -> None:
    # MSFT is targeted, leaves (auto-close), rejoins; rebalance() must not
    # resurrect the stale target.
    frames = {"AAPL": _frame([10.0] * 10), "MSFT": _frame([20.0] * 10)}
    universe = Universe(
        [
            Membership("AAPL"),
            Membership("MSFT", end=_t(4)),
            Membership("MSFT", start=_t(7)),
        ]
    )

    class SetOnce(Strategy):
        def __init__(self) -> None:
            self.post_rejoin_orders = []

        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("MSFT", 0.5)
            orders = ctx.rebalance()
            if ctx.time.day >= 7:
                self.post_rejoin_orders.extend(orders)

    strategy = SetOnce()
    result = run_portfolio_backtest(
        frames=frames,
        strategy=strategy,
        starting_cash=1_000.0,
        universe=universe,
        costs=Costs.frictionless(),
    )
    assert strategy.post_rejoin_orders == []
    assert result.equity_curve[-1].weights == {}  # auto-closed, never re-bought


def test_target_without_a_revealed_bar_is_deferred() -> None:
    # MSFT is in the universe from day 1 but its data starts day 3: rebalance
    # cannot size it without a mark, so the order appears once data exists.
    frames = {"AAPL": _frame([10.0] * 5), "MSFT": _frame([20.0] * 3, start_day=3)}

    class Eager(Strategy):
        def on_bar(self, ctx) -> None:
            ctx.target_weight("MSFT", 0.5)
            ctx.rebalance()

    result = run_portfolio_backtest(
        frames=frames,
        strategy=Eager(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    msft_fills = [f for f in result.fills if f.symbol == "MSFT"]
    assert len(msft_fills) > 0
    assert min(f.fill_index for f in msft_fills) == 3  # sized day 3, filled day 4


def test_context_exposes_current_weights_and_targets() -> None:
    frames = {"AAPL": _frame([10.0] * 4)}

    class Inspect(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                assert ctx.weights == {}
                ctx.target_weight("AAPL", 0.4)
                assert ctx.targets == {"AAPL": 0.4}
                ctx.rebalance()
            if ctx.time.day >= 2:
                assert ctx.weights == {"AAPL": 0.4}

    run_portfolio_backtest(
        frames=frames,
        strategy=Inspect(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
