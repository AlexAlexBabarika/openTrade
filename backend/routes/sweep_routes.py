# backend/routes/sweep_routes.py
"""Parameter sweep + walk-forward endpoints.

Start a sweep (202 + sweep_id), poll its progress, cancel it, introspect a
strategy's parameter schema, drill into a single trial as a full BacktestResult,
and run walk-forward synchronously. Compute happens off-request on the
``SweepRegistry`` daemon thread; the client polls — no WebSocket. Market data is
loaded with the same cache+provider path as ``/scripts/execute``.
"""

from __future__ import annotations

import logging

import polars as pl
import requests
from fastapi import APIRouter, HTTPException, status
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.backtesting.engine import run_backtest
from backend.backtesting.optimize.jobs import SweepRegistry
from backend.backtesting.optimize.serialize import walk_forward_to_dict
from backend.backtesting.optimize.types import SweepConfig
from backend.backtesting.optimize.walkforward import run_walk_forward
from backend.backtesting.sandbox import (
    _FunctionStrategy,
    _strategy_globals,
    parse_strategy_schema,
)
from backend.backtesting.serialize import result_to_dict
from backend.market import cache
from backend.market.ohlcv_limits import cap_candles
from backend.market.shared_config import validate_interval, validate_period
from backend.models.market_data_models import MarketDataProviderEnum
from backend.routes.market_routes import _fetch_candles_blocking
from backend.routes.script_routes import _candles_to_df
from backend.scripts.ast_guard import ScriptValidationError, validate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sweeps", tags=["sweeps"])
_registry = SweepRegistry()


class SchemaRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=200_000)


class _DataRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=200_000)
    symbol: str = Field(..., min_length=1)
    provider: MarketDataProviderEnum
    period: str = "1y"
    interval: str = "1d"
    starting_cash: float = 100_000.0


class SweepRequest(_DataRequest):
    search: str = "grid"
    metric: str = "sharpe"
    vary: list[str]
    fixed: dict = Field(default_factory=dict)
    n_random: int = Field(200, gt=0, le=10_000)
    seed: int = 0


class WalkForwardRequest(SweepRequest):
    is_len: int = Field(..., gt=0)
    oos_len: int = Field(..., gt=0)
    step: int = Field(..., gt=0)
    anchored: bool = False


async def _load_frame(body: _DataRequest) -> tuple[pl.DataFrame, str]:
    """Fetch (or cache-hit) candles and return (frame, data_version)."""
    sym = body.symbol.strip()
    try:
        validate_period(body.period)
        validate_interval(body.interval)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    candles = cache.get_cached(
        body.provider.value, sym, period=body.period, interval=body.interval
    )
    if not candles:
        try:
            candles = await run_in_threadpool(
                _fetch_candles_blocking,
                body.provider,
                sym,
                body.period,
                body.interval,
                None,
            )
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
        except (requests.HTTPError, APIError, RuntimeError) as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
        candles = cap_candles(candles)
        cache.set_cached(
            body.provider.value,
            sym,
            candles,
            period=body.period,
            interval=body.interval,
        )
    if not candles:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No data for '{sym}'")

    frame = _candles_to_df(candles)
    data_version = (
        f"{body.provider.value}:{sym}:{body.period}:{body.interval}:{frame.height}"
    )
    return frame, data_version


@router.post("/schema")
def schema(body: SchemaRequest) -> dict:
    try:
        parsed = parse_strategy_schema(body.code)
    except ScriptValidationError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"strategy rejected: {e}"
        ) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return {"schema": {name: p.to_dict() for name, p in parsed.items()}}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_sweep(body: SweepRequest) -> dict:
    try:
        validate(body.code)
    except ScriptValidationError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"strategy rejected: {e}"
        ) from e
    frame, data_version = await _load_frame(body)
    config = SweepConfig(
        search=body.search,
        metric=body.metric,
        vary=body.vary,
        n_random=body.n_random,
        seed=body.seed,
        starting_cash=body.starting_cash,
        data_version=data_version,
        fixed=body.fixed,
    )
    sweep_id = _registry.start(code=body.code, frame=frame, config=config)
    return {"sweep_id": sweep_id}


@router.get("/{sweep_id}")
def poll_sweep(sweep_id: str) -> dict:
    job = _registry.get(sweep_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown sweep {sweep_id}")
    return {
        "sweep_id": job.sweep_id,
        "status": job.status,
        "total": job.total,
        "done": job.done,
        "trials": job.trials,
        "best_trial_id": job.best_trial_id,
        "error": job.error,
        "result": job.result,
    }


@router.delete("/{sweep_id}", status_code=status.HTTP_202_ACCEPTED)
def cancel_sweep(sweep_id: str) -> dict:
    if not _registry.cancel(sweep_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown sweep {sweep_id}")
    return {"sweep_id": sweep_id, "status": "cancelling"}


@router.get("/{sweep_id}/trial/{trial_id}")
async def trial_result(
    sweep_id: str,
    trial_id: int,
    symbol: str,
    provider: MarketDataProviderEnum,
    code: str,
    period: str = "1y",
    interval: str = "1d",
    starting_cash: float = 100_000.0,
) -> dict:
    """Re-run a single trial's params and return its full BacktestResult blob.

    Re-running is cheap (one backtest) and avoids holding every trial's full blob
    in memory; determinism guarantees the dashboard sees the same numbers the
    sweep reported for this trial.
    """
    job = _registry.get(sweep_id)
    if job is None or job.result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sweep not finished")
    trial = next((t for t in job.result["trials"] if t["trial_id"] == trial_id), None)
    if trial is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown trial {trial_id}")

    body = _DataRequest(
        code=code,
        symbol=symbol,
        provider=provider,
        period=period,
        interval=interval,
        starting_cash=starting_cash,
    )
    frame, _ = await _load_frame(body)
    g = _strategy_globals()
    exec(compile(code, "<strategy>", "exec"), g)
    result = await run_in_threadpool(
        run_backtest,
        frame=frame,
        strategy=_FunctionStrategy(g["on_bar"]),
        starting_cash=starting_cash,
        seed=job.result["config"]["seed"],
        params=trial["params"],
    )
    return result_to_dict(result)


@router.post("/walk-forward")
async def walk_forward(body: WalkForwardRequest) -> dict:
    try:
        validate(body.code)
    except ScriptValidationError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"strategy rejected: {e}"
        ) from e
    frame, data_version = await _load_frame(body)
    config = SweepConfig(
        search=body.search,
        metric=body.metric,
        vary=body.vary,
        n_random=body.n_random,
        seed=body.seed,
        starting_cash=body.starting_cash,
        data_version=data_version,
        fixed=body.fixed,
    )
    try:
        report = await run_in_threadpool(
            run_walk_forward,
            code=body.code,
            frame=frame,
            config=config,
            is_len=body.is_len,
            oos_len=body.oos_len,
            step=body.step,
            anchored=body.anchored,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return walk_forward_to_dict(report)
