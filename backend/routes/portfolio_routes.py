# backend/routes/portfolio_routes.py
"""Portfolio (multi-asset) backtest endpoint.

Runs one strategy script against a universe of symbols inside the spawn
sandbox (``run_portfolio_strategy``) and returns the full canonical portfolio
blob plus run status and captured stdout/stderr. Market data per symbol is
loaded with the same cache+provider path as ``/backtests`` and ``/sweeps``;
constraints declared in the request are enforced by the engine and their
bindings come back in ``constraint_events``.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.backtesting.multi.constraints import Constraints
from backend.backtesting.multi.sandbox import (
    parse_portfolio_strategy_schema,
    run_portfolio_strategy,
)
from backend.models.market_data_models import MarketDataProviderEnum
from backend.routes.sweep_routes import _load_frame
from backend.scripts.ast_guard import ScriptValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio-backtests", tags=["portfolio-backtests"])

_RUN_TIMEOUT_S = 30.0
_MAX_SYMBOLS = 50


class ConstraintsModel(BaseModel):
    max_position_weight: float | None = None
    max_position_value: float | None = None
    max_sector_weight: float | None = None
    sectors: dict[str, str] = Field(default_factory=dict)
    long_only: bool = False
    no_short: list[str] = Field(default_factory=list)
    no_trade: list[str] = Field(default_factory=list)
    max_gross: float | None = None
    max_net: float | None = None
    min_trade_value: float = 0.0

    def to_constraints(self) -> Constraints:
        return Constraints(
            max_position_weight=self.max_position_weight,
            max_position_value=self.max_position_value,
            max_sector_weight=self.max_sector_weight,
            sectors=self.sectors or None,
            long_only=self.long_only,
            no_short=frozenset(self.no_short),
            no_trade=frozenset(self.no_trade),
            max_gross=self.max_gross,
            max_net=self.max_net,
            min_trade_value=self.min_trade_value,
        )


class PortfolioRunRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=200_000)
    symbols: list[str] = Field(..., min_length=1, max_length=_MAX_SYMBOLS)
    provider: MarketDataProviderEnum
    period: str = "1y"
    interval: str = "1d"
    starting_cash: float = 100_000.0
    seed: int = 0
    params: dict = Field(default_factory=dict)
    constraints: ConstraintsModel | None = None


@dataclasses.dataclass
class _SymbolDataRequest:
    """Shim matching the attribute shape ``_load_frame`` reads."""

    symbol: str
    provider: MarketDataProviderEnum
    period: str
    interval: str


@router.post("/run")
async def run(body: PortfolioRunRequest) -> dict:
    try:
        schema = parse_portfolio_strategy_schema(body.code)
    except ScriptValidationError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"strategy rejected: {e}"
        ) from e
    defaults = {name: p.values()[0] for name, p in schema.items()}
    params = {**defaults, **body.params}

    symbols = sorted({s.strip() for s in body.symbols if s.strip()})
    if not symbols:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no symbols given")

    loaded = await asyncio.gather(
        *(
            _load_frame(
                _SymbolDataRequest(
                    symbol=symbol,
                    provider=body.provider,
                    period=body.period,
                    interval=body.interval,
                )
            )
            for symbol in symbols
        )
    )
    frames = {symbol: frame for symbol, (frame, _) in zip(symbols, loaded)}

    result = await run_in_threadpool(
        run_portfolio_strategy,
        body.code,
        frames,
        starting_cash=body.starting_cash,
        timeout_s=_RUN_TIMEOUT_S,
        seed=body.seed,
        params=params,
        constraints=body.constraints.to_constraints() if body.constraints else None,
    )
    return dataclasses.asdict(result)
