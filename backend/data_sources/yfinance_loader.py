"""
yfinance data loader. Fetches OHLCV and normalizes to unified schema.
"""

from datetime import datetime, timezone
from typing import Any

import yfinance as yf
from backend.models import OHLCVCandle
from backend.normalizer import normalize_rows


def load_yfinance(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
) -> list[OHLCVCandle]:
    """
    Load OHLCV for symbol from Yahoo Finance.
    Returns list of OHLCVCandle in unified schema (UTC ISO8601).
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    if df is None or df.empty:
        return []
    # yfinance columns: Open, High, Low, Close, Volume, index is Datetime
    df = df.reset_index()
    df.columns = [c.strip() for c in df.columns]
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        ts = row.get("Date", row.get("Datetime"))
        if ts is None:
            continue
        if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            ts = ts.replace(tzinfo=timezone.utc) if hasattr(ts, "replace") else ts
        rows.append(
            {
                "Date": ts,
                "Open": float(row.get("Open", 0)),
                "High": float(row.get("High", 0)),
                "Low": float(row.get("Low", 0)),
                "Close": float(row.get("Close", 0)),
                "Volume": float(row.get("Volume", 0)),
            }
        )
    return normalize_rows(rows, symbol)
