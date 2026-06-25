"""Run a user portfolio strategy script through the engine inside the sandbox.

Same spawn-isolation, resource limits, and network block as the single-symbol
``backtesting.sandbox``, but the child drives ``run_portfolio_backtest`` over
one frame per symbol. The strategy namespace additionally exposes the sizers
and rebalance policies (pure objects with no I/O surface), so portfolio
scripts can write ``equal_weight(ctx.universe)`` or hold a
``PeriodicRebalance("monthly")`` without imports.
"""

from __future__ import annotations

import io
import time
import traceback
from dataclasses import dataclass, field
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

import polars as pl

from backend.backtesting.errors import EngineError
from backend.backtesting.multi.constraints import Constraints
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.universe import Universe
from backend.backtesting.multi.policies import (
    PeriodicRebalance,
    SignalRebalance,
    ThresholdRebalance,
)
from backend.backtesting.multi.serialize import portfolio_result_to_dict
from backend.backtesting.multi.sizers import (
    equal_weight,
    inverse_volatility,
    kelly_weight,
    kelly_weights,
    trailing_volatility,
)
from backend.backtesting.optimize.space import Choice, Float, Int, parse_schema
from backend.backtesting.strategy import Strategy
from backend.scripts.ast_guard import ScriptValidationError, validate
from backend.scripts.runner import (
    _apply_resource_limits,
    _block_network,
    spawn_and_collect,
)
from backend.scripts.sandbox_globals import _SAFE_BUILTINS

DEFAULT_TIMEOUT_S = 10.0
DEFAULT_MEMORY_MB = 512
DEFAULT_STARTING_CASH = 100_000.0


@dataclass
class PortfolioStrategyRunResult:
    status: str  # "ok" | "error" | "timeout" | "killed"
    meta: dict = field(default_factory=dict)
    symbols: list[str] = field(default_factory=list)
    bars: dict = field(default_factory=dict)
    orders: list[dict] = field(default_factory=list)
    fills: list[dict] = field(default_factory=list)
    equity: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    constraint_events: list[dict] = field(default_factory=list)
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


def _portfolio_globals() -> dict[str, Any]:
    """Strategy namespace: safe builtins, schema types, sizers, and policies.

    Everything injected is a pure value object or pure function — no I/O
    surface beyond what the single-symbol sandbox already allows."""
    return {
        "__builtins__": _SAFE_BUILTINS,
        "Int": Int,
        "Float": Float,
        "Choice": Choice,
        "equal_weight": equal_weight,
        "inverse_volatility": inverse_volatility,
        "kelly_weight": kelly_weight,
        "kelly_weights": kelly_weights,
        "trailing_volatility": trailing_volatility,
        "PeriodicRebalance": PeriodicRebalance,
        "ThresholdRebalance": ThresholdRebalance,
        "SignalRebalance": SignalRebalance,
    }


def parse_portfolio_strategy_schema(code: str) -> dict:
    """Validate ``code`` and return its declared parameter schema (may be empty).

    The portfolio counterpart of ``backtesting.sandbox.parse_strategy_schema``:
    the module body is evaluated in the *portfolio* namespace, so module-level
    use of the injected sizers/policies (``policy = PeriodicRebalance(...)``)
    parses instead of failing with a NameError. Same caveat as the single-
    symbol version: this exec runs in-process without resource limits, so
    callers must gate request size/rate.
    """
    validate(code)
    g = _portfolio_globals()
    try:
        exec(compile(code, "<strategy>", "exec"), g)
        return parse_schema(g)
    except ScriptValidationError:
        raise
    except Exception as e:  # normalize bad-params / module-body errors
        raise ScriptValidationError(f"could not evaluate strategy schema: {e}") from e


def _child_main(
    conn,
    code: str,
    frames: dict[str, pl.DataFrame],
    starting_cash: float,
    seed: int,
    params: dict | None,
    constraints: Constraints | None,
    universe: "Universe | None",
    data_version: str | None,
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
            g = _portfolio_globals()
            exec(compiled, g)
            on_bar = g.get("on_bar")
            if not callable(on_bar):
                raise EngineError("strategy must define an on_bar(ctx) function")
            result = run_portfolio_backtest(
                frames=frames,
                strategy=_FunctionStrategy(on_bar),
                starting_cash=starting_cash,
                constraints=constraints,
                seed=seed,
                params=params,
                universe=universe,
                data_version=data_version,
            )
        payload.update(portfolio_result_to_dict(result))
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


def run_portfolio_strategy(
    code: str,
    frames: dict[str, pl.DataFrame],
    *,
    starting_cash: float = DEFAULT_STARTING_CASH,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    seed: int = 0,
    params: dict | None = None,
    constraints: Constraints | None = None,
    universe: Universe | None = None,
    data_version: str | None = None,
) -> PortfolioStrategyRunResult:
    """Validate and run a portfolio strategy script against ``frames``."""
    started = time.monotonic()
    try:
        validate(code)
    except ScriptValidationError as e:
        return PortfolioStrategyRunResult(
            status="error",
            stderr=f"strategy rejected: {e}\n",
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )

    payload, timed_out, exitcode = spawn_and_collect(
        _child_main,
        (
            code,
            frames,
            starting_cash,
            seed,
            params,
            constraints,
            universe,
            data_version,
        ),
        timeout_s,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if timed_out:
        return PortfolioStrategyRunResult(
            status="timeout",
            stderr=f"strategy exceeded {timeout_s}s wallclock timeout\n",
            elapsed_ms=elapsed_ms,
        )
    if payload is None:
        return PortfolioStrategyRunResult(
            status="killed",
            stderr=f"strategy exited without returning a result (exitcode={exitcode})\n",
            elapsed_ms=elapsed_ms,
        )

    return PortfolioStrategyRunResult(
        status=payload.get("status", "ok"),
        meta=payload.get("meta", {}),
        symbols=payload.get("symbols", []),
        bars=payload.get("bars", {}),
        orders=payload.get("orders", []),
        fills=payload.get("fills", []),
        equity=payload.get("equity", []),
        trades=payload.get("trades", []),
        constraint_events=payload.get("constraint_events", []),
        metrics=payload.get("metrics", {}),
        stdout=payload.get("stdout", ""),
        stderr=payload.get("stderr", ""),
        elapsed_ms=elapsed_ms,
    )
