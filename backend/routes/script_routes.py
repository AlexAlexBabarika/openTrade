"""User-script execution endpoint (phase 1 — no persistence).

Resolves OHLCV server-side for the requested (provider, symbol, interval,
period) and runs the supplied Python `code` in a sandboxed subprocess.
"""

from __future__ import annotations

import logging

import pandas as pd
import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.core.auth_deps import optional_current_user
from backend.core.rate_limit import allow, client_key, retry_after_seconds
from backend.market import cache
from backend.market.ohlcv_limits import cap_candles
from backend.market.shared_config import validate_interval, validate_period
from backend.models.auth_models import AuthUserInfo
from backend.models.market_data_models import MarketDataProviderEnum
from backend.routes.market_routes import _fetch_candles_blocking
from backend.scripts.output_models import RunResult
from backend.scripts.runner import run_script


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scripts", tags=["scripts"])


class ExecuteRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=200_000)
    symbol: str = Field(..., min_length=1)
    provider: MarketDataProviderEnum
    period: str = "1mo"
    interval: str = "1d"
    timeout_s: float = Field(5.0, gt=0, le=30)
    memory_mb: int = Field(256, gt=0, le=1024)


def _candles_to_df(candles) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).astype(
            float
        )
    rows = [
        {
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    return df


@router.post("/execute", response_model=RunResult)
async def execute(
    body: ExecuteRequest,
    request: Request,
    user: AuthUserInfo | None = Depends(optional_current_user),
) -> RunResult:
    if not allow(client_key(request.client.host if request.client else None)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many script runs. Try again shortly.",
            headers={"Retry-After": str(retry_after_seconds())},
        )

    sym = body.symbol.strip()
    try:
        validate_period(body.period)
        validate_interval(body.interval)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    if body.provider is MarketDataProviderEnum.twelvedata and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Twelve Data requires authentication.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    candles = cache.get_cached(body.provider.value, sym)
    if not candles:
        try:
            candles = await run_in_threadpool(
                _fetch_candles_blocking,
                body.provider,
                sym,
                body.period,
                body.interval,
                user,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except (requests.HTTPError, APIError, RuntimeError) as e:
            logger.warning("Script: provider error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)
            ) from e
        except Exception as e:
            logger.exception("Script: market data fetch failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to load market data",
            ) from e
        candles = cap_candles(candles)
        cache.set_cached(body.provider.value, sym, candles)

    if not candles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data available for '{sym}'",
        )

    df = _candles_to_df(candles)
    return await run_in_threadpool(
        run_script,
        body.code,
        df,
        timeout_s=body.timeout_s,
        memory_mb=body.memory_mb,
    )
