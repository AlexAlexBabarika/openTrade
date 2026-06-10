"""
The portfolio engine drives the aligned multi-symbol timeline: per event it
reveals bars, fills resting orders, enforces universe membership (a strategy
can only see and trade symbols active at the current bar; positions in
departing symbols are auto-closed through the normal order path, so the exit
pays realistic costs and shows up in the trade log), calls the strategy, and
marks the book to the latest known closes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from backend.backtesting.costs import (
    Costs,
    FixedBpsHalfSpread,
    FixedBpsSlippage,
    PerShareCommission,
)
from backend.backtesting.errors import UniverseError
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.universe import Membership, Universe
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import OrderType, Side


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


class BuyEachOnce(Strategy):
    """Buy 1 share of every symbol in the universe on its first visible bar."""

    def __init__(self) -> None:
        self.bought: set[str] = set()

    def on_bar(self, ctx) -> None:
        for symbol in ctx.universe:
            if symbol not in self.bought:
                ctx.buy(symbol, 1.0)
                self.bought.add(symbol)


class Recorder(Strategy):
    """Record what the context exposes at every bar."""

    def __init__(self) -> None:
        self.seen: list[tuple[int, tuple[str, ...]]] = []

    def on_bar(self, ctx) -> None:
        self.seen.append((ctx.time.day, ctx.universe))


def test_buy_and_hold_two_symbols_marks_both_positions() -> None:
    frames = {"AAPL": _frame([10.0] * 5), "MSFT": _frame([20.0] * 5)}
    result = run_portfolio_backtest(
        frames=frames,
        strategy=BuyEachOnce(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    assert len(result.equity_curve) == 5
    # Orders submitted on day 1 fill at day 2's opens: 10 + 20 spent.
    final = result.equity_curve[-1]
    assert final.cash == 1_000.0 - 30.0
    assert final.equity == 1_000.0  # flat prices, frictionless
    assert final.weights == {"AAPL": 10.0 / 1_000.0, "MSFT": 20.0 / 1_000.0}
    assert [f.symbol for f in result.fills] == ["AAPL", "MSFT"]
    assert all(f.fill_index == 1 for f in result.fills)


def test_universe_membership_gates_visibility_and_trading() -> None:
    frames = {"AAPL": _frame([10.0] * 6), "MSFT": _frame([20.0] * 6)}
    universe = Universe(
        [Membership("AAPL"), Membership("MSFT", start=_t(3), end=_t(5))]
    )
    recorder = Recorder()
    run_portfolio_backtest(
        frames=frames,
        strategy=recorder,
        starting_cash=1_000.0,
        universe=universe,
        costs=Costs.frictionless(),
    )
    assert recorder.seen == [
        (1, ("AAPL",)),
        (2, ("AAPL",)),
        (3, ("AAPL", "MSFT")),
        (4, ("AAPL", "MSFT")),
        (5, ("AAPL",)),
        (6, ("AAPL",)),
    ]


def test_reading_or_trading_an_inactive_symbol_raises() -> None:
    frames = {"AAPL": _frame([10.0] * 3), "MSFT": _frame([20.0] * 3)}
    far_future = datetime(2030, 1, 1, tzinfo=timezone.utc)
    universe = Universe([Membership("AAPL"), Membership("MSFT", start=far_future)])

    class Peeker(Strategy):
        def __init__(self) -> None:
            self.errors: list[str] = []

        def on_bar(self, ctx) -> None:
            with pytest.raises(UniverseError):
                ctx.bars["MSFT"]
            with pytest.raises(UniverseError):
                ctx.buy("MSFT", 1.0)
            assert "MSFT" not in ctx.bars
            assert ctx.bars["AAPL"][-1].close == 10.0

    run_portfolio_backtest(
        frames=frames,
        strategy=Peeker(),
        starting_cash=1_000.0,
        universe=universe,
        costs=Costs.frictionless(),
    )


def test_symbol_leaving_universe_closes_its_position_with_costs() -> None:
    frames = {"AAPL": _frame([10.0] * 6), "MSFT": _frame([20.0] * 6)}
    universe = Universe([Membership("AAPL"), Membership("MSFT", end=_t(4))])
    costs = Costs(
        slippage=FixedBpsSlippage(0.0),
        spread=FixedBpsHalfSpread(0.0),
        commission=PerShareCommission(1.0),
    )
    result = run_portfolio_backtest(
        frames=frames,
        strategy=BuyEachOnce(),
        starting_cash=1_000.0,
        universe=universe,
        costs=costs,
    )
    # MSFT bought (fills day 2), leaves at day 4 -> auto-close submitted day 4,
    # fills day 5 at MSFT's open, paying commission.
    msft_fills = [f for f in result.fills if f.symbol == "MSFT"]
    assert [f.side for f in msft_fills] == [Side.BUY, Side.SELL]
    assert msft_fills[1].fill_index == 4
    assert msft_fills[1].commission == 1.0

    msft_trades = [t for t in result.trades if t.symbol == "MSFT"]
    assert len(msft_trades) == 1
    assert msft_trades[0].pnl == -2.0  # flat price, 2x $1 commission

    assert result.equity_curve[-1].weights.keys() == {"AAPL"}


def test_resting_orders_for_departed_symbol_are_cancelled() -> None:
    frames = {"AAPL": _frame([10.0] * 6), "MSFT": _frame([20.0] * 6)}
    universe = Universe([Membership("AAPL"), Membership("MSFT", end=_t(3))])

    class LowballMsft(Strategy):
        def __init__(self) -> None:
            self.done = False

        def on_bar(self, ctx) -> None:
            if not self.done and "MSFT" in ctx.bars:
                ctx.buy("MSFT", 1.0, type=OrderType.LIMIT, limit=1.0)  # never fillable
                self.done = True

    result = run_portfolio_backtest(
        frames=frames,
        strategy=LowballMsft(),
        starting_cash=1_000.0,
        universe=universe,
        costs=Costs.frictionless(),
    )
    assert result.fills == []


def test_unknown_universe_symbol_is_rejected_up_front() -> None:
    with pytest.raises(UniverseError):
        run_portfolio_backtest(
            frames={"AAPL": _frame([10.0])},
            strategy=Recorder(),
            starting_cash=1_000.0,
            universe=Universe.static(["AAPL", "TSLA"]),
        )


def test_runs_are_deterministic() -> None:
    frames = {
        "AAPL": _frame([10.0, 11.0, 9.0, 12.0]),
        "MSFT": _frame([20.0, 19.0, 21.0, 22.0]),
    }

    class FlipFlop(Strategy):
        def on_bar(self, ctx) -> None:
            for symbol in ctx.universe:
                if ctx.random.random() < 0.5:
                    ctx.buy(symbol, 1.0)
                elif ctx.position(symbol).quantity > 0:
                    ctx.sell(symbol, 1.0)

    a = run_portfolio_backtest(
        frames=frames, strategy=FlipFlop(), starting_cash=1_000.0, seed=7
    )
    b = run_portfolio_backtest(
        frames=frames, strategy=FlipFlop(), starting_cash=1_000.0, seed=7
    )
    assert [p.equity for p in a.equity_curve] == [p.equity for p in b.equity_curve]
    assert [(f.symbol, f.price) for f in a.fills] == [
        (f.symbol, f.price) for f in b.fills
    ]


def test_trades_are_symbol_stamped_and_chronological() -> None:
    frames = {"AAPL": _frame([10.0] * 6), "MSFT": _frame([20.0] * 6)}

    class RoundTrips(Strategy):
        def on_bar(self, ctx) -> None:
            day = ctx.time.day
            if day == 1:
                ctx.buy("MSFT", 1.0)
            elif day == 2:
                ctx.sell("MSFT", 1.0)
                ctx.buy("AAPL", 1.0)
            elif day == 4:
                ctx.sell("AAPL", 1.0)

    result = run_portfolio_backtest(
        frames=frames,
        strategy=RoundTrips(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    assert [(t.symbol, t.exit_index) for t in result.trades] == [
        ("MSFT", 2),
        ("AAPL", 4),
    ]


def test_context_exposes_portfolio_state() -> None:
    frames = {"AAPL": _frame([10.0] * 4)}

    class Checker(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                assert ctx.cash == 1_000.0
                assert ctx.equity == 1_000.0
                assert ctx.positions == {}
                ctx.buy("AAPL", 2.0)
            if ctx.time.day >= 2:
                assert ctx.position("AAPL").quantity == 2.0
                assert ctx.cash == 1_000.0 - 20.0
                assert ctx.equity == 1_000.0
                assert list(ctx.positions) == ["AAPL"]

    run_portfolio_backtest(
        frames=frames,
        strategy=Checker(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
