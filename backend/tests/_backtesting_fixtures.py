"""Shared canonical strategy + data for the determinism tests.

Importable from both the test module and a subprocess (to prove the equity
curve hash does not depend on PYTHONHASHSEED), so the exact same run is
reproduced in each.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl

from backend.backtesting.engine import equity_curve_hash, run_backtest
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import BacktestResult


class BuyAndHold(Strategy):
    """Buy a fixed quantity on the first bar, then hold."""

    def __init__(self) -> None:
        self._bought = False

    def on_bar(self, ctx) -> None:
        if not self._bought:
            ctx.buy(10.0)
            self._bought = True


class CoinFlip(Strategy):
    """Stochastic strategy: drives trades off ctx.random to test seeding."""

    def on_bar(self, ctx) -> None:
        if ctx.position.quantity == 0.0:
            if ctx.random.random() < 0.5:
                ctx.buy(1.0)
        else:
            ctx.sell(1.0)


def canonical_frame(n: int = 50) -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(days=i) for i in range(n)]
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.standard_normal(n))
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.full(n, 1000.0),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


def canonical_result() -> BacktestResult:
    return run_backtest(
        frame=canonical_frame(),
        strategy=BuyAndHold(),
        starting_cash=10_000.0,
        seed=0,
    )


def canonical_hash() -> str:
    return equity_curve_hash(canonical_result().equity_curve)
