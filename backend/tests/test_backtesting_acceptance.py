"""The execution engine's three acceptance criteria, as CI guards.

1. Buy-and-hold on 10y daily data runs in <2s with realistic costs.
2. The same run twice produces byte-identical equity curves.
3. A strategy that reads bar[t+1] raises a clear engine error, not a silent
    success.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
import pytest

from backend.backtesting.costs import Costs
from backend.backtesting.engine import equity_curve_hash, run_backtest
from backend.backtesting.errors import LookAheadError
from backend.backtesting.sandbox import run_strategy
from backend.backtesting.strategy import Strategy

TRADING_DAYS_PER_YEAR = 252
TEN_YEARS = 10 * TRADING_DAYS_PER_YEAR  # ~2520 daily bars


def _daily_frame(n: int = TEN_YEARS) -> pl.DataFrame:
    """A deterministic ~10y daily OHLCV frame standing in for SPY."""
    start = datetime(2014, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(days=i) for i in range(n)]
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.standard_normal(n) * 0.5)
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


class _BuyAndHold(Strategy):
    def on_bar(self, ctx) -> None:
        if ctx.position.quantity == 0.0:
            ctx.buy(100.0)


class _PeeksAhead(Strategy):
    def on_bar(self, ctx) -> None:
        _ = ctx.bars[ctx.bars.index + 1]  # the next (future) bar


# --- criterion 1: performance ----------------------------------------------


def test_buy_and_hold_10y_daily_runs_under_2s_with_realistic_costs() -> None:
    frame = _daily_frame()
    start = time.perf_counter()
    result = run_backtest(
        frame=frame,
        strategy=_BuyAndHold(),
        starting_cash=1_000_000.0,
        costs=Costs.default(),  # realistic, conservative costs
    )
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"engine took {elapsed:.3f}s on 10y daily"
    assert len(result.equity_curve) == TEN_YEARS
    assert len(result.fills) == 1  # bought once, then held


# --- criterion 2: determinism ----------------------------------------------


def test_identical_runs_produce_byte_identical_equity_curves() -> None:
    frame = _daily_frame()
    a = run_backtest(frame=frame, strategy=_BuyAndHold(), starting_cash=1_000_000.0)
    b = run_backtest(frame=frame, strategy=_BuyAndHold(), starting_cash=1_000_000.0)
    assert a.equity_curve == b.equity_curve
    assert equity_curve_hash(a.equity_curve) == equity_curve_hash(b.equity_curve)


# --- criterion 3: look-ahead is a hard error -------------------------------


def test_engine_raises_lookahead_error_when_strategy_reads_the_future() -> None:
    with pytest.raises(LookAheadError):
        run_backtest(
            frame=_daily_frame(n=10),
            strategy=_PeeksAhead(),
            starting_cash=1_000_000.0,
        )


def test_strategy_script_reading_future_bar_surfaces_a_clear_error() -> None:
    code = "def on_bar(ctx):\n    nxt = ctx.bars[ctx.bars.index + 1]\n"
    res = run_strategy(code, _daily_frame(n=10), timeout_s=10.0)
    assert res.status == "error"
    assert "future" in res.stderr
