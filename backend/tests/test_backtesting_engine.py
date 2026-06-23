"""End-to-end run loop and determinism guarantees.

The engine wires loop + context + broker + portfolio behind a Strategy.on_bar
callback. Determinism is the point: a single seed threads into ctx.random,
output ordering is stable, and the same inputs produce a byte-identical equity
curve. A golden hash guards against silent drift, and a subprocess check proves
the hash is independent of PYTHONHASHSEED.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import polars as pl

from backend.backtesting.costs import Costs
from backend.backtesting.engine import equity_curve_hash, run_backtest
from backend.backtesting.strategy import Strategy
from backend.tests._backtesting_fixtures import (
    CoinFlip,
    canonical_frame,
    canonical_hash,
)

# Captured once from a real run; regenerate intentionally if the engine changes.
GOLDEN_EQUITY_HASH = "7a1f7865e6824aaf8235e43980d5fe88a29d40250cbf468ff5899b6b33b2e1ad"


class _BuyOnceTen(Strategy):
    def __init__(self) -> None:
        self._bought = False

    def on_bar(self, ctx) -> None:
        if not self._bought:
            ctx.buy(10.0)
            self._bought = True


def _frame(opens: list[float], closes: list[float]) -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(days=i) for i in range(len(opens))]
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": opens,
            "high": [max(o, c) + 1 for o, c in zip(opens, closes)],
            "low": [min(o, c) - 1 for o, c in zip(opens, closes)],
            "close": closes,
            "volume": [1000.0] * len(opens),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


def test_buy_and_hold_equity_curve() -> None:
    frame = _frame(opens=[100.0, 110.0, 130.0], closes=[100.0, 120.0, 130.0])
    result = run_backtest(
        frame=frame,
        strategy=_BuyOnceTen(),
        starting_cash=10_000.0,
        costs=Costs.frictionless(),
    )
    equities = [p.equity for p in result.equity_curve]
    # bar0: flat -> 10000; bar1: bought 10 @110 (-1100), mark 120 -> 10100;
    # bar2: mark 130 -> 10200.
    assert equities == [10_000.0, 10_100.0, 10_200.0]


def test_result_records_orders_and_fills() -> None:
    frame = _frame(opens=[100.0, 110.0, 130.0], closes=[100.0, 120.0, 130.0])
    result = run_backtest(
        frame=frame,
        strategy=_BuyOnceTen(),
        starting_cash=10_000.0,
        costs=Costs.frictionless(),
    )
    assert len(result.orders) == 1
    assert len(result.fills) == 1
    assert result.fills[0].price == 110.0


def test_two_runs_are_byte_identical() -> None:
    a = run_backtest(
        frame=canonical_frame(), strategy=CoinFlip(), starting_cash=10_000.0, seed=42
    )
    b = run_backtest(
        frame=canonical_frame(), strategy=CoinFlip(), starting_cash=10_000.0, seed=42
    )
    assert equity_curve_hash(a.equity_curve) == equity_curve_hash(b.equity_curve)
    assert a.equity_curve == b.equity_curve
    assert a.fills == b.fills


def test_seed_threads_into_ctx_random() -> None:
    # Same seed -> identical stochastic path; different seed -> different path.
    base = run_backtest(
        frame=canonical_frame(), strategy=CoinFlip(), starting_cash=10_000.0, seed=1
    )
    same = run_backtest(
        frame=canonical_frame(), strategy=CoinFlip(), starting_cash=10_000.0, seed=1
    )
    other = run_backtest(
        frame=canonical_frame(), strategy=CoinFlip(), starting_cash=10_000.0, seed=2
    )
    assert base.fills == same.fills
    assert base.fills != other.fills


def test_golden_equity_curve_hash() -> None:
    assert canonical_hash() == GOLDEN_EQUITY_HASH


def test_equity_curve_hash_is_independent_of_pythonhashseed() -> None:
    def _hash_with(hashseed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": hashseed}
        out = subprocess.run(
            [
                sys.executable,
                "-c",
                "from backend.tests._backtesting_fixtures import canonical_hash;"
                "print(canonical_hash())",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        return out.stdout.strip()

    assert _hash_with("0") == _hash_with("1")


def test_run_backtest_produces_full_result():
    from backend.backtesting.engine import run_backtest
    from backend.backtesting.types import Metrics
    from backend.tests._backtesting_fixtures import BuyAndHold, canonical_frame

    result = run_backtest(
        frame=canonical_frame(),
        strategy=BuyAndHold(),
        starting_cash=10_000.0,
        seed=7,
        strategy_id="buy_and_hold",
        params={"qty": 10},
    )

    assert result.meta.seed == 7
    assert result.meta.strategy_id == "buy_and_hold"
    assert result.meta.params == {"qty": 10}
    assert result.meta.run_id  # non-empty
    assert result.meta.finished_at >= result.meta.started_at
    assert len(result.bars) == len(result.equity_curve)
    assert isinstance(result.metrics, Metrics)
    # BuyAndHold opens but never closes -> no completed round trips.
    assert result.trades == []
    assert len(result.fills) == 1
