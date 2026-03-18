"""
In-memory cache for loaded OHLCV data (keyed by symbol and optional source id).
"""

from typing import Any

from backend.market.models import OHLCVCandle

# symbol -> list of candles (for REST/WS)
_data_cache: dict[str, list[OHLCVCandle]] = {}
# optional: (symbol, "csv") for CSV uploads to avoid key clash with yfinance
_csv_keys: set[str] = set()


def get_cached(symbol: str) -> list[OHLCVCandle] | None:
    """Return cached candles for symbol or None."""
    return _data_cache.get(symbol)


def set_cached(symbol: str, candles: list[OHLCVCandle]) -> None:
    """Store candles in cache for symbol."""
    _data_cache[symbol] = candles


def set_cached_csv(symbol: str, candles: list[OHLCVCandle]) -> None:
    """Mark symbol as CSV-sourced and cache."""
    _csv_keys.add(symbol)
    _data_cache[symbol] = candles


def is_csv_cached(symbol: str) -> bool:
    return symbol in _csv_keys


def list_cached_symbols() -> list[str]:
    """Return all symbols currently in cache."""
    return list(_data_cache.keys())
