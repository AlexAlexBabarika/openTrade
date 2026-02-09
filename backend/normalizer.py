"""
Normalizes raw OHLCV data into the unified schema.
Maps various column names (Date, Open, o, etc.) to canonical: timestamp, open, high, low, close, volume.
Ensures UTC ISO8601 timestamps.
"""

from datetime import datetime, timezone
from typing import Any

from backend.models import OHLCVCandle

# Column name mappings: Date, Datetime, time, timestamp → timestamp; Open, o → open; etc.
COLUMN_ALIASES = {
    "timestamp": ("date", "datetime", "time", "timestamp", "dt", "t"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "v", "vol"),
}


def _normalize_column_name(name: str) -> str | None:
    """Map a column name to canonical key, or None if not OHLCV-related."""
    if not name or not isinstance(name, str):
        return None
    key = name.strip().lower()
    for canonical, aliases in COLUMN_ALIASES.items():
        if key in aliases:
            return canonical
    return None


def _parse_timestamp(value: Any) -> datetime:
    """Parse value to UTC datetime. Returns naive UTC."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        # Unix timestamp (seconds or ms)
        if value > 1e12:
            value = value / 1000.0
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        # Try ISO format first
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
        ):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                break
            except ValueError:
                continue
        else:
            from dateutil import parser as date_parser
            dt = date_parser.parse(value)
    else:
        raise ValueError(f"Cannot parse timestamp: {value!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)  # naive UTC for JSON


def _to_float(value: Any) -> float:
    """Coerce to float for OHLCV numeric fields."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "")
    return float(s)


def normalize_row(row: dict[str, Any], symbol: str) -> OHLCVCandle:
    """Convert a single row (dict with arbitrary keys) to OHLCVCandle."""
    mapped: dict[str, Any] = {}
    for raw_key, raw_value in row.items():
        canon = _normalize_column_name(raw_key)
        if canon is None:
            continue
        if canon == "timestamp":
            mapped[canon] = _parse_timestamp(raw_value)
        elif canon == "volume":
            mapped[canon] = _to_float(raw_value)
        else:
            mapped[canon] = _to_float(raw_value)
    if "timestamp" not in mapped:
        raise ValueError("Row missing timestamp")
    for key in ("open", "high", "low", "close", "volume"):
        mapped.setdefault(key, 0.0)
    # Avoid validation error: open/close must be > 0
    if mapped.get("open", 0) <= 0 and mapped.get("close", 0) > 0:
        mapped["open"] = mapped["close"]
    elif mapped.get("close", 0) <= 0 and mapped.get("open", 0) > 0:
        mapped["close"] = mapped["open"]
    elif mapped.get("open", 0) <= 0 and mapped.get("close", 0) <= 0:
        mapped["open"] = mapped["close"] = 0.01
    mapped["symbol"] = symbol
    return OHLCVCandle(**mapped)


def normalize_rows(rows: list[dict[str, Any]], symbol: str) -> list[OHLCVCandle]:
    """Convert multiple rows to list of OHLCVCandles."""
    return [normalize_row(r, symbol) for r in rows]
