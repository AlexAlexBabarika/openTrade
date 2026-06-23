"""Run a user strategy script through the engine inside the sandbox.

The engine sits underneath the existing script runner: this module reuses the
runner's spawn-isolation, resource limits, and network block, but instead of
the whole-series display globals it executes the strategy's ``on_bar(ctx)``
function and drives ``run_backtest`` in the child. The result is the full
canonical blob (meta, bars, orders, fills, equity, trades, metrics) as
serializable dicts, or a clear error/timeout.
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
from backend.backtesting.optimize.space import Choice, Float, Int, parse_schema
from backend.backtesting.serialize import result_to_dict
from backend.backtesting.strategy import Strategy
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
    meta: dict = field(default_factory=dict)
    bars: list[dict] = field(default_factory=list)
    orders: list[dict] = field(default_factory=list)
    fills: list[dict] = field(default_factory=list)
    equity: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
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
    """Namespace for executing a strategy script: safe builtins + schema types.

    No whole-series data and no ``np``/``pl``. ``Int``/``Float``/``Choice`` are
    injected so a strategy can declare ``params = {...}``; they are plain value
    objects with no I/O surface.
    """
    return {
        "__builtins__": _SAFE_BUILTINS,
        "Int": Int,
        "Float": Float,
        "Choice": Choice,
    }


# Sizers/policies injected only by the portfolio sandbox. Referencing one from a
# single-symbol strategy is the most common confusing NameError, so we translate
# it into "use the Portfolio tab". Source of truth: multi.sandbox
# ._portfolio_globals (kept in sync by test_backtesting_sandbox).
_PORTFOLIO_ONLY_NAMES = frozenset(
    {
        "equal_weight",
        "inverse_volatility",
        "kelly_weight",
        "kelly_weights",
        "trailing_volatility",
        "PeriodicRebalance",
        "ThresholdRebalance",
        "SignalRebalance",
    }
)


def _child_main(
    conn,
    code: str,
    df: pl.DataFrame,
    starting_cash: float,
    seed: int,
    params: dict | None,
) -> None:
    """Picklable child entrypoint: build the strategy and run the backtest."""
    _apply_resource_limits(DEFAULT_MEMORY_MB)
    _block_network()

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    payload: dict = {"status": "ok", "stdout": "", "stderr": ""}
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
                params=params,
            )
        payload.update(result_to_dict(result))
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
    params: dict | None = None,
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
        _child_main, (code, df, starting_cash, seed, params), timeout_s
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
        meta=payload.get("meta", {}),
        bars=payload.get("bars", []),
        orders=payload.get("orders", []),
        fills=payload.get("fills", []),
        equity=payload.get("equity", []),
        trades=payload.get("trades", []),
        metrics=payload.get("metrics", {}),
        stdout=payload.get("stdout", ""),
        stderr=payload.get("stderr", ""),
        elapsed_ms=elapsed_ms,
    )


def parse_strategy_schema(code: str) -> dict:
    """Validate ``code`` and return its declared parameter schema (may be empty).

    Executes the module body in the strategy sandbox namespace to materialize the
    ``params`` declaration, then validates each entry is an Int/Float/Choice. Any
    failure — unsafe code, a malformed ``params`` declaration, or an error raised
    while evaluating the module body — surfaces as ``ScriptValidationError`` so
    callers have a single exception contract.

    Note: the AST guard is the security control, but it does not bound CPU/memory.
    This exec runs in-process with no resource limits, so a syntactically valid but
    expensive declaration (e.g. a giant comprehension) can exhaust resources.
    Callers exposing this to untrusted input must gate request size / rate, or run
    it behind the spawn sandbox used by ``run_strategy``.
    """
    validate(code)
    g = _strategy_globals()
    try:
        exec(compile(code, "<strategy>", "exec"), g)
        return parse_schema(g)
    except ScriptValidationError:
        raise
    except NameError as e:
        if e.name in _PORTFOLIO_ONLY_NAMES:
            raise ScriptValidationError(
                f"{e.name!r} is a portfolio-only feature — run multi-asset "
                f"strategies from the Portfolio tab."
            ) from e
        raise ScriptValidationError(f"could not evaluate strategy schema: {e}") from e
    except Exception as e:  # normalize bad-params / module-body errors
        raise ScriptValidationError(f"could not evaluate strategy schema: {e}") from e
