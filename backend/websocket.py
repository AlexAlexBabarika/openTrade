"""
WebSocket broadcaster: streams OHLCV candles to clients progressively.
"""

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from backend.models import OHLCVCandle


def candle_to_json(c: OHLCVCandle) -> dict[str, Any]:
    """Serialize candle for WebSocket (timestamp as ISO8601 string)."""
    return {
        "symbol": c.symbol,
        "timestamp": c.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume,
    }


async def stream_candles(
    websocket: WebSocket,
    candles: list[OHLCVCandle],
    delay_seconds: float = 0.02,
) -> None:
    """
    Send candles to client one by one with small delay (progressive streaming).
    """
    for c in candles:
        try:
            await websocket.send_json(candle_to_json(c))
            await asyncio.sleep(delay_seconds)
        except Exception:
            break
