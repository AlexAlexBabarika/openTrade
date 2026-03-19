"""
Unified market data (OHLCV) endpoint.

Providers that need user API keys (Twelve Data) require a Bearer token.
Binance and yfinance work without auth; optional auth can improve Binance limits.
"""

import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.auth_deps import optional_current_user
from backend.market import cache
from backend.market.data_sources import load_binance, load_yfinance
from backend.market.data_sources.twelvedataprovider import TwelveDataProvider
from backend.market.data_sources.binance_loader import BinanceProvider
from backend.market.models import OHLCVCandleList
from backend.models.auth_models import AuthUserInfo
from backend.models.market_data_models import MarketDataProviderEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["market"])


def _fetch_candles(
    provider: MarketDataProviderEnum,
    symbol: str,
    period: str,
    interval: str,
    user: AuthUserInfo | None,
) -> list:
    sym = symbol.strip()
    if not sym:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="symbol is required",
        )

    if provider is MarketDataProviderEnum.yfinance:
        return load_yfinance(symbol=sym, period=period, interval=interval)

    if provider is MarketDataProviderEnum.binance:
        uid = user.id if user else None
        return BinanceProvider(user_id=uid).get_ohlcv(sym, period, interval)

    if provider is MarketDataProviderEnum.twelvedata:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Twelve Data requires authentication. Send Authorization: Bearer <token>.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TwelveDataProvider(user.id).get_ohlcv(sym, period, interval)


@router.get("/market", response_model=OHLCVCandleList)
def get_market_ohlcv(
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
    try:
        candles = _fetch_candles(provider, symbol, period, interval, user)
    except HTTPException:
        raise
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

    sym = symbol.strip()
    cache.set_cached(sym, candles)
    return OHLCVCandleList(symbol=sym, candles=candles)
