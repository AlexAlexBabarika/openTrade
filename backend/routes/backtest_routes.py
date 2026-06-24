# backend/routes/backtest_routes.py
"""Single-run backtest endpoint.

Runs one strategy script against market data inside the spawn sandbox
(``run_strategy``) and returns the full canonical result blob plus run status
and captured stdout/stderr. Param values default to the first value of each
declared ``params`` entry; the request may override any of them. Market data
is loaded with the same cache+provider path as ``/sweeps``.
"""

from __future__ import annotations

import dataclasses
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.backtesting.run_config import RunInputs
from backend.backtesting.run_snapshot import assemble_snapshot
from backend.backtesting.run_store import RunStore
from backend.backtesting.sandbox import parse_strategy_schema, run_strategy
from backend.models.market_data_models import MarketDataProviderEnum
from backend.routes.sweep_routes import _load_frame
from backend.scripts.ast_guard import ScriptValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtests", tags=["backtests"])

_RUN_STORE = RunStore.default()

_RUN_TIMEOUT_S = 30.0


class BacktestRunRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=200_000)
    symbol: str = Field(..., min_length=1)
    provider: MarketDataProviderEnum
    period: str = "1y"
    interval: str = "1d"
    starting_cash: float = 100_000.0
    seed: int = 0
    params: dict = Field(default_factory=dict)


@router.post("/run")
async def run(body: BacktestRunRequest) -> dict:
    try:
        schema = parse_strategy_schema(body.code)
    except ScriptValidationError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"strategy rejected: {e}"
        ) from e
    defaults = {name: p.values()[0] for name, p in schema.items()}
    params = {**defaults, **body.params}

    frame, data_version = await _load_frame(body)
    result = await run_in_threadpool(
        run_strategy,
        body.code,
        frame,
        starting_cash=body.starting_cash,
        timeout_s=_RUN_TIMEOUT_S,
        seed=body.seed,
        params=params,
    )
    blob = dataclasses.asdict(result)
    if result.status == "ok":
        inputs = RunInputs(
            code=body.code,
            params=params,
            data_version=data_version,
            seed=body.seed,
            starting_cash=body.starting_cash,
        )
        blob["run_id"] = _RUN_STORE.write(assemble_snapshot(blob, inputs))
    return blob
