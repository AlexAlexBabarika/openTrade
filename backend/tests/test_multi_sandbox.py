"""
run_portfolio_strategy executes a user script's on_bar(ctx) against multiple
frames inside the same spawn sandbox as single-symbol runs (AST guard,
resource limits, network block), with the sizers and rebalance policies
pre-injected into the strategy namespace.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl

from backend.backtesting.multi.constraints import Constraints
from backend.backtesting.multi.sandbox import run_portfolio_strategy


def _frame(seed: int, n: int = 40) -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(days=i) for i in range(n)]
    close = 100 + np.cumsum(np.random.default_rng(seed).standard_normal(n) * 0.5)
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 1e6),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


FRAMES = {"AAPL": _frame(0), "MSFT": _frame(1)}

EQUAL_WEIGHT_CODE = """
policy = PeriodicRebalance("monthly")

def on_bar(ctx):
    for symbol, weight in equal_weight(ctx.universe).items():
        ctx.target_weight(symbol, weight)
    if policy.should_rebalance(ctx):
        ctx.rebalance()
"""


def test_equal_weight_script_runs_with_injected_helpers() -> None:
    result = run_portfolio_strategy(EQUAL_WEIGHT_CODE, FRAMES, starting_cash=10_000.0)
    assert result.status == "ok", result.stderr
    assert result.symbols == ["AAPL", "MSFT"]
    assert len(result.fills) >= 2
    assert {f["symbol"] for f in result.fills} == {"AAPL", "MSFT"}
    assert result.equity[-1]["weights"]
    assert "sharpe" in result.metrics["portfolio"]
    assert set(result.metrics["symbol_sharpes"]) == {"AAPL", "MSFT"}


def test_constraints_flow_through_to_the_run() -> None:
    result = run_portfolio_strategy(
        EQUAL_WEIGHT_CODE,
        FRAMES,
        starting_cash=10_000.0,
        constraints=Constraints(max_position_weight=0.1),
    )
    assert result.status == "ok", result.stderr
    assert any(
        e["constraint"] == "max_position_weight" for e in result.constraint_events
    )
    final_weights = result.equity[-1]["weights"]
    assert all(abs(w) <= 0.11 for w in final_weights.values())


def test_script_without_on_bar_errors() -> None:
    result = run_portfolio_strategy("x = 1\n", FRAMES)
    assert result.status == "error"
    assert "on_bar" in result.stderr


def test_unsafe_script_is_rejected_before_spawning() -> None:
    result = run_portfolio_strategy("import os\ndef on_bar(ctx): pass\n", FRAMES)
    assert result.status == "error"
    assert "rejected" in result.stderr
