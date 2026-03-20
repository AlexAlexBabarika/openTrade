"""
Unified market data (OHLCV) endpoint.

Providers that need user API keys (Twelve Data) require a Bearer token.
Binance and yfinance work without auth; optional auth can improve Binance limits.
"""

from __future__ import annotations

import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from backend.core.auth_deps import optional_current_user
from backend.core.rate_limit import allow, client_key, retry_after_seconds
from backend.market import cache
from backend.market.data_sources import load_yfinance
from backend.market.data_sources.twelvedataprovider import TwelveDataProvider
from backend.market.data_sources.binance_loader import BinanceProvider
from backend.market.models import OHLCVCandleList
from backend.market.ohlcv_limits import cap_candles
from backend.market.shared_config import validate_interval, validate_period
from backend.models.auth_models import AuthUserInfo
from backend.models.market_data_models import MarketDataProviderEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["market"])


def _fetch_candles_blocking(
    provider: MarketDataProviderEnum,
    symbol: str,
    period: str,
    interval: str,
    user: AuthUserInfo | None,
) -> list:
    """Blocking provider I/O only (run in a thread pool)."""
    sym = symbol.strip()
    if provider is MarketDataProviderEnum.yfinance:
        return load_yfinance(symbol=sym, period=period, interval=interval)

    if provider is MarketDataProviderEnum.binance:
        uid = user.id if user else None
        return BinanceProvider(user_id=uid).get_ohlcv(sym, period, interval)

    if provider is MarketDataProviderEnum.twelvedata:
        if user is None:
            # Explicit guard (not assert): survives ``python -O``; route should 401 first.
            raise RuntimeError(
                "Twelve Data requires an authenticated user; route auth check was skipped."
            )
        return TwelveDataProvider(user.id).get_ohlcv(sym, period, interval)

    raise RuntimeError(f"Unsupported provider: {provider}")


@router.get("/market", response_model=OHLCVCandleList)
async def get_market_ohlcv(
    request: Request,
    response: Response,
    symbol: str = Query(
        ..., min_length=1, description="Instrument symbol (e.g. AAPL, BTCUSDT)"
    ),
    provider: MarketDataProviderEnum = Query(
        ...,
        description="Data provider: yfinance, twelvedata, or binance",
    ),
    period: str = Query(
        "1mo",
        description="Lookback period (e.g. 1d, 5d, 1w, 1mo, 3mo, 6mo, 1y)",
    ),
    interval: str = Query(
        "1d",
        description="Bar size (e.g. 1m, 5m, 1h, 1d, 1w, 1mo); provider-specific",
    ),
    user: AuthUserInfo | None = Depends(optional_current_user),
) -> OHLCVCandleList:
    """
    Load OHLCV candles for a symbol from the chosen provider.

    - **yfinance**: no auth.
    - **binance**: optional auth (optional API key in settings for higher limits).
    - **twelvedata**: requires Bearer token and a stored Twelve Data API key.
    """
    if not allow(client_key(request.client.host if request.client else None)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many market data requests. Try again shortly.",
            headers={"Retry-After": str(retry_after_seconds())},
        )

    sym = symbol.strip()
    if not sym:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="symbol is required",
        )

    try:
        validate_period(period)
        validate_interval(interval)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if provider is MarketDataProviderEnum.twelvedata and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Twelve Data requires authentication. Send Authorization: Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        candles = await run_in_threadpool(
            _fetch_candles_blocking,
            provider,
            sym,
            period,
            interval,
            user,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except requests.HTTPError as e:
        logger.warning("Market data HTTP error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except APIError as e:
        logger.warning("Market data: PostgREST error (e.g. API key lookup): %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Database error while loading provider configuration.",
        ) from e
    except RuntimeError as e:
        logger.warning("Market data provider error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Market data fetch failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load market data",
        ) from e

    before = len(candles)
    candles = cap_candles(candles)
    if before > len(candles):
        response.headers["X-OHLCV-Truncated"] = "true"
        response.headers["X-OHLCV-Truncated-From"] = str(before)

    cache.set_cached(provider.value, sym, candles)
    return OHLCVCandleList(symbol=sym, candles=candles)
