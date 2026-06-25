"""Run a user strategy script through the engine inside the sandbox.

The engine sits underneath the existing script runner: this module reuses the
runner's spawn-isolation, resource limits, and network block, but instead of
the whole-series display globals it executes the strategy's ``on_bar(ctx)``
function and drives ``run_backtest`` in the child. The result is a serializable
equity curve plus fills, or a clear error/timeout.
"""

from __future__ import annotations

import io
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from typing import Any

import polars as pl

from backend.backtesting.engine import run_backtest
from backend.backtesting.errors import EngineError
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import Fill
from backend.scripts.ast_guard import ScriptValidationError, validate
from backend.scripts.runner import (
    _apply_resource_limits,
    _block_network,
    spawn_and_collect,
)
from backend.scripts.sandbox_globals import _SAFE_BUILTINS

DEFAULT_TIMEOUT_S = 5.0
DEFAULT_MEMORY_MB = 512
DEFAULT_STARTING_CASH = 100_000.0


@dataclass
class StrategyRunResult:
    status: str  # "ok" | "error" | "timeout" | "killed"
    equity_curve: list[dict] = field(default_factory=list)
    fills: list[dict] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: int = 0


class _FunctionStrategy(Strategy):
    """Adapts a user ``on_bar`` function into the Strategy contract."""

    def __init__(self, on_bar) -> None:
        self._on_bar = on_bar

    def on_bar(self, ctx) -> None:
        self._on_bar(ctx)


def _strategy_globals() -> dict[str, Any]:
    """Namespace for executing a strategy script: safe builtins only.

    No whole-series data (the strategy sees data only through ``ctx``) and no
    ``np``/``pl`` — numpy in particular exposes file I/O (np.load/fromfile).
    Strategies needing maths can import the AST-allowed stdlib (math/statistics).
    """
    return {"__builtins__": _SAFE_BUILTINS}


def _serialize_fill(f: Fill) -> dict:
    return {
        "submitted_index": f.submitted_index,
        "fill_index": f.fill_index,
        "side": f.side.value,
        "quantity": f.quantity,
        "price": f.price,
        "reference_price": f.reference_price,
        "slippage": f.slippage,
        "spread_cost": f.spread_cost,
        "commission": f.commission,
        "reason": f.reason,
    }


def _child_main(
    conn, code: str, df: pl.DataFrame, starting_cash: float, seed: int
) -> None:
    """Picklable child entrypoint: build the strategy and run the backtest."""
    _apply_resource_limits(DEFAULT_MEMORY_MB)
    _block_network()

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    payload: dict = {
        "status": "ok",
        "equity_curve": [],
        "fills": [],
        "stdout": "",
        "stderr": "",
    }
    try:
        compiled = compile(code, "<strategy>", "exec")
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            g = _strategy_globals()
            exec(compiled, g)
            on_bar = g.get("on_bar")
            if not callable(on_bar):
                raise EngineError("strategy must define an on_bar(ctx) function")
            result = run_backtest(
                frame=df,
                strategy=_FunctionStrategy(on_bar),
                starting_cash=starting_cash,
                seed=seed,
            )
        payload["equity_curve"] = [
            {"time": int(p.time.timestamp()), "equity": p.equity}
            for p in result.equity_curve
        ]
        payload["fills"] = [_serialize_fill(f) for f in result.fills]
    except SystemExit:
        payload["status"] = "killed"
        stderr_buf.write("strategy called sys.exit / exit()\n")
    except BaseException:
        payload["status"] = "error"
        stderr_buf.write(traceback.format_exc())

    payload["stdout"] = stdout_buf.getvalue()
    payload["stderr"] = stderr_buf.getvalue()
    try:
        conn.send(payload)
    except Exception:
        pass
    finally:
        conn.close()


def run_strategy(
    code: str,
    df: pl.DataFrame,
    *,
    starting_cash: float = DEFAULT_STARTING_CASH,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    seed: int = 0,
) -> StrategyRunResult:
    """Validate and run a strategy script against `df`, returning its result."""
    started = time.monotonic()
    try:
        validate(code)
    except ScriptValidationError as e:
        return StrategyRunResult(
            status="error",
            stderr=f"strategy rejected: {e}\n",
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )

    payload, timed_out, exitcode = spawn_and_collect(
        _child_main, (code, df, starting_cash, seed), timeout_s
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if timed_out:
        return StrategyRunResult(
            status="timeout",
            stderr=f"strategy exceeded {timeout_s}s wallclock timeout\n",
            elapsed_ms=elapsed_ms,
        )
    if payload is None:
        return StrategyRunResult(
            status="killed",
            stderr=f"strategy exited without returning a result (exitcode={exitcode})\n",
            elapsed_ms=elapsed_ms,
        )

    return StrategyRunResult(
        status=payload.get("status", "ok"),
        equity_curve=payload.get("equity_curve", []),
        fills=payload.get("fills", []),
        stdout=payload.get("stdout", ""),
        stderr=payload.get("stderr", ""),
        elapsed_ms=elapsed_ms,
    )
