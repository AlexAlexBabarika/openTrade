"""The portfolio workstream's three acceptance criteria, as CI guards.

1. A 50-symbol monthly-rebalanced strategy runs in <10s on 10 years of daily
   data, with realistic costs.
2. Removing a symbol from the universe mid-backtest closes its position with
   realistic costs and the exit appears in the trade log.
3. Portfolio Sharpe is reported alongside individual-symbol Sharpes.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl

from backend.backtesting.costs import Costs
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.policies import PeriodicRebalance
from backend.backtesting.multi.sizers import equal_weight
from backend.backtesting.multi.universe import Membership, Universe
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import Side

TRADING_DAYS_PER_YEAR = 252
TEN_YEARS = 10 * TRADING_DAYS_PER_YEAR  # ~2520 daily bars
N_SYMBOLS = 50

_START = datetime(2014, 1, 1, tzinfo=timezone.utc)


def _daily_frame(seed: int, n: int = TEN_YEARS) -> pl.DataFrame:
    ts = [_START + timedelta(days=i) for i in range(n)]
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.standard_normal(n) * 0.5)
    close = np.maximum(close, 1.0)  # keep prices positive
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 1_000_000.0),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


class MonthlyEqualWeight(Strategy):
    def __init__(self) -> None:
        self.policy = PeriodicRebalance("monthly")

    def on_bar(self, ctx) -> None:
        if self.policy.should_rebalance(ctx):
            for symbol, weight in equal_weight(ctx.universe).items():
                ctx.target_weight(symbol, weight)
            ctx.rebalance(min_trade_value=50.0)


def test_50_symbols_10y_monthly_rebalance_under_10s() -> None:
    frames = {f"SYM{i:02d}": _daily_frame(seed=i) for i in range(N_SYMBOLS)}

    started = time.monotonic()
    result = run_portfolio_backtest(
        frames=frames,
        strategy=MonthlyEqualWeight(),
        starting_cash=1_000_000.0,
        costs=Costs.default(),  # realistic costs, not frictionless
    )
    elapsed = time.monotonic() - started

    assert elapsed < 10.0, f"portfolio engine took {elapsed:.2f}s on 50x10y daily"
    assert len(result.equity_curve) == TEN_YEARS
    # The portfolio actually held the universe.
    assert len(result.equity_curve[-1].weights) == N_SYMBOLS
    # Criterion 3: portfolio Sharpe alongside all individual-symbol Sharpes.
    assert isinstance(result.metrics.portfolio.sharpe, float)
    assert len(result.metrics.symbol_sharpes) == N_SYMBOLS
    assert result.metrics.turnover_annualized > 0.0


def test_mid_backtest_universe_removal_closes_with_costs() -> None:
    n = 60
    frames = {
        "KEEP": _daily_frame(seed=1, n=n),
        "GONE": _daily_frame(seed=2, n=n),
    }
    leave = _START + timedelta(days=30)
    universe = Universe([Membership("KEEP"), Membership("GONE", end=leave)])

    class HoldBoth(Strategy):
        def on_bar(self, ctx) -> None:
            for symbol in ctx.universe:
                if ctx.position(symbol).quantity == 0.0:
                    ctx.buy(symbol, 10.0)

    result = run_portfolio_backtest(
        frames=frames,
        strategy=HoldBoth(),
        starting_cash=100_000.0,
        universe=universe,
        costs=Costs.default(),
    )

    # The departed symbol's position was flattened through the normal order
    # path: a closing sell fill that paid commission, after the leave date.
    gone_fills = [f for f in result.fills if f.symbol == "GONE"]
    assert [f.side for f in gone_fills] == [Side.BUY, Side.SELL]
    closing = gone_fills[-1]
    assert closing.commission > 0.0
    assert closing.fill_index >= 30
    # ... and the round trip appears in the trade log.
    gone_trades = [t for t in result.trades if t.symbol == "GONE"]
    assert len(gone_trades) == 1
    # No position or weight remains at the end.
    assert "GONE" not in result.equity_curve[-1].weights
