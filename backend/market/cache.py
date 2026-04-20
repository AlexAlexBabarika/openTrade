"""
In-memory cache for loaded OHLCV data.

Keys are ``provider:symbol`` so different providers never overwrite the same symbol.
"""

from typing import Any

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


# ---------------------------------------------------------------------------
# Volume-profile cache
# Keyed by (provider, symbol, start_ts, end_ts, row_size, va_pct, interval).
# Values are arbitrary result objects (ProfileResult from volume_profile.py).
# ---------------------------------------------------------------------------

_profile_cache: dict[tuple, Any] = {}


def make_profile_key(
    provider: str,
    symbol: str,
    start_ts: int,
    end_ts: int | None,
    row_size: float,
    va_pct: float,
    interval: str,
) -> tuple:
    return (
        provider.strip().lower(),
        symbol.strip(),
        int(start_ts),
        int(end_ts) if end_ts is not None else None,
        round(float(row_size), 8),
        round(float(va_pct), 6),
        interval.strip().lower(),
    )


def get_cached_profile(key: tuple) -> Any | None:
    return _profile_cache.get(key)


def set_cached_profile(key: tuple, value: Any) -> None:
    _profile_cache[key] = value


def clear_profile_cache() -> None:
    _profile_cache.clear()
