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
    assert len(res.equity) == 30
    assert len(res.bars) == 30
    assert len(res.fills) == 1
    assert res.fills[0]["side"] == "buy"
    assert res.metrics["total_return"] is not None
    assert res.meta["seed"] == 0


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


def test_strategy_cannot_advance_the_bar_cursor(df: pl.DataFrame) -> None:
    # The cursor is the engine's; a strategy must not be able to reveal the
    # next bar early. The read-only view has no advance().
    code = "def on_bar(ctx):\n    ctx.bars.advance()\n"
    res = run_strategy(code, df, timeout_s=10.0)
    assert res.status == "error"


def test_strategy_cannot_reach_the_underlying_bar_list(df: pl.DataFrame) -> None:
    # Underscore attribute access (which would expose future bars) is rejected
    # by the AST guard before the code runs.
    code = "def on_bar(ctx):\n    everything = ctx.bars._series\n"
    res = run_strategy(code, df, timeout_s=10.0)
    assert res.status == "error"
    assert "not allowed" in res.stderr


def test_strategy_namespace_excludes_numpy(df: pl.DataFrame) -> None:
    # np exposes file I/O (np.load/fromfile); strategies reach data via ctx only.
    code = "def on_bar(ctx):\n    np.array([1, 2, 3])\n"
    res = run_strategy(code, df, timeout_s=10.0)
    assert res.status == "error"


def test_run_strategy_returns_canonical_blob_keys(df: pl.DataFrame) -> None:
    code = "def on_bar(ctx):\n    pass\n"
    res = run_strategy(code, df, timeout_s=10.0)

    assert res.status == "ok", res.stderr
    assert res.meta != {}
    assert isinstance(res.trades, list)
    assert "max_drawdown" in res.metrics


def test_parse_strategy_schema_reads_declared_params() -> None:
    from backend.backtesting.sandbox import parse_strategy_schema

    code = (
        "params = {\n"
        "    'fast': Int(5, 50, step=5),\n"
        "    'stop': Float(0.5, 5.0, step=0.5),\n"
        "    'regime': Choice(['trend', 'meanrev']),\n"
        "}\n"
        "def on_bar(ctx):\n"
        "    pass\n"
    )
    schema = parse_strategy_schema(code)
    assert set(schema) == {"fast", "stop", "regime"}
    assert schema["fast"].values() == [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]


def test_parse_strategy_schema_empty_when_no_params() -> None:
    from backend.backtesting.sandbox import parse_strategy_schema

    assert parse_strategy_schema("def on_bar(ctx):\n    pass\n") == {}


def test_parse_strategy_schema_rejects_unsafe_code() -> None:
    from backend.backtesting.sandbox import parse_strategy_schema
    from backend.scripts.ast_guard import ScriptValidationError

    with pytest.raises(ScriptValidationError):
        parse_strategy_schema("import os\ndef on_bar(ctx):\n    pass\n")


def test_parse_strategy_schema_normalizes_bad_params_to_validation_error() -> None:
    # A malformed `params` (not a dict of Param) surfaces as ScriptValidationError,
    # not a raw ValueError, so callers have one exception contract.
    from backend.backtesting.sandbox import parse_strategy_schema
    from backend.scripts.ast_guard import ScriptValidationError

    with pytest.raises(ScriptValidationError):
        parse_strategy_schema("params = 42\ndef on_bar(ctx):\n    pass\n")


@pytest.mark.parametrize("name", ["PeriodicRebalance", "ThresholdRebalance"])
def test_portfolio_only_name_points_to_portfolio_tab(name: str) -> None:
    # Rebalance policies / sizers only exist in the multi-asset sandbox; using
    # one in a single-symbol strategy gets actionable guidance, not a raw
    # NameError.
    from backend.backtesting.sandbox import parse_strategy_schema
    from backend.scripts.ast_guard import ScriptValidationError

    code = f"policy = {name}('monthly')\ndef on_bar(ctx):\n    pass\n"
    with pytest.raises(ScriptValidationError) as exc:
        parse_strategy_schema(code)
    msg = str(exc.value)
    assert name in msg
    assert "Portfolio tab" in msg


def test_unknown_name_keeps_generic_schema_error() -> None:
    # A genuinely undefined name is still reported the old way.
    from backend.backtesting.sandbox import parse_strategy_schema
    from backend.scripts.ast_guard import ScriptValidationError

    with pytest.raises(ScriptValidationError) as exc:
        parse_strategy_schema("x = totally_undefined\ndef on_bar(ctx):\n    pass\n")
    assert "could not evaluate strategy schema" in str(exc.value)


def test_portfolio_only_names_stay_in_sync_with_portfolio_globals() -> None:
    # Drift guard: the hardcoded set must match what the portfolio sandbox
    # actually injects beyond the single-asset namespace.
    from backend.backtesting.sandbox import _PORTFOLIO_ONLY_NAMES, _strategy_globals
    from backend.backtesting.multi.sandbox import _portfolio_globals

    extra = set(_portfolio_globals()) - set(_strategy_globals())
    assert _PORTFOLIO_ONLY_NAMES == frozenset(extra)


def test_run_strategy_passes_params_to_ctx(df: pl.DataFrame) -> None:
    code = (
        "params = {'qty': Int(1, 4, step=1)}\n"
        "def on_bar(ctx):\n"
        "    if ctx.position.quantity == 0:\n"
        "        ctx.buy(ctx.params['qty'])\n"
    )
    res = run_strategy(
        code, df, starting_cash=100_000.0, timeout_s=10.0, params={"qty": 3}
    )
    assert res.status == "ok", res.stderr
    assert res.fills[0]["quantity"] == 3
    assert res.meta["params"] == {"qty": 3}
