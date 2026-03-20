"""
In-memory cache for loaded OHLCV data.

Keys are ``provider:symbol`` so different providers never overwrite the same symbol.
"""

from backend.market.models import OHLCVCandle

# "provider:symbol" -> candles
_data_cache: dict[str, list[OHLCVCandle]] = {}
# Symbols that were loaded via CSV (same logical key as csv:symbol)
_csv_keys: set[str] = set()


def make_cache_key(provider: str, symbol: str) -> str:
    """Build cache key: ``provider:symbol`` (normalized)."""
    p = provider.strip().lower()
    s = symbol.strip()
    return f"{p}:{s}"


def get_cached(provider: str, symbol: str) -> list[OHLCVCandle] | None:
    """Return cached candles for provider+symbol or None."""
    return _data_cache.get(make_cache_key(provider, symbol))


def set_cached(provider: str, symbol: str, candles: list[OHLCVCandle]) -> None:
    """Store candles under provider:symbol."""
    _data_cache[make_cache_key(provider, symbol)] = candles


def set_cached_csv(symbol: str, candles: list[OHLCVCandle]) -> None:
    """Cache CSV upload under provider ``csv``."""
    key = make_cache_key("csv", symbol)
    _csv_keys.add(key)
    _data_cache[key] = candles


def is_csv_cached(symbol: str) -> bool:
    return make_cache_key("csv", symbol) in _csv_keys


def list_cached_keys() -> list[str]:
    """Return all cache keys (``provider:symbol``)."""
    return list(_data_cache.keys())
