"""API models for unified market data endpoints."""

from enum import Enum


class MarketDataProviderEnum(str, Enum):
    """Supported OHLCV data providers for GET /data/market."""

    yfinance = "yfinance"
    twelvedata = "twelvedata"
    binance = "binance"
