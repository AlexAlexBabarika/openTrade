"""Running a user strategy script through the sandboxed engine.

A strategy is authored as a top-level ``on_bar(ctx)`` function. run_strategy
validates it (reusing the AST guard), executes it inside the spawn-isolated
child process the script runner already uses, and runs the backtest engine
there, returning a serializable result (equity curve + fills) or a clear error.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
import pytest

from backend.backtesting.sandbox import run_strategy


@pytest.fixture
def df() -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(days=i) for i in range(30)]
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.standard_normal(30))
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.full(30, 1000.0),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


def test_buy_and_hold_strategy_runs_end_to_end(df: pl.DataFrame) -> None:
    code = (
        "def on_bar(ctx):\n"
        "    if ctx.position.quantity == 0:\n"
        "        ctx.buy(10)\n"
    )
    res = run_strategy(code, df, starting_cash=100_000.0, timeout_s=10.0)
    assert res.status == "ok", res.stderr
    assert len(res.equity_curve) == 30
    assert len(res.fills) == 1
    assert res.fills[0]["side"] == "buy"


def test_strategy_can_use_ctx_state(df: pl.DataFrame) -> None:
    code = (
        "def on_bar(ctx):\n"
        "    ctx.state['n'] = ctx.state.get('n', 0) + 1\n"
        "    if ctx.state['n'] == 1:\n"
        "        ctx.buy(5)\n"
    )
    res = run_strategy(code, df, starting_cash=100_000.0, timeout_s=10.0)
    assert res.status == "ok", res.stderr
    assert len(res.fills) == 1
    assert res.fills[0]["quantity"] == 5.0


def test_strategy_without_on_bar_is_rejected(df: pl.DataFrame) -> None:
    res = run_strategy("x = 1\n", df, timeout_s=10.0)
    assert res.status == "error"
    assert "on_bar" in res.stderr


def test_strategy_runtime_error_is_surfaced(df: pl.DataFrame) -> None:
    code = "def on_bar(ctx):\n    raise ValueError('boom')\n"
    res = run_strategy(code, df, timeout_s=10.0)
    assert res.status == "error"
    assert "boom" in res.stderr


def test_disallowed_import_is_rejected(df: pl.DataFrame) -> None:
    code = "import os\ndef on_bar(ctx):\n    pass\n"
    res = run_strategy(code, df, timeout_s=10.0)
    assert res.status == "error"
    assert "not allowed" in res.stderr


def test_infinite_loop_times_out(df: pl.DataFrame) -> None:
    code = "def on_bar(ctx):\n    while True:\n        pass\n"
    res = run_strategy(code, df, timeout_s=1.0)
    assert res.status == "timeout"
