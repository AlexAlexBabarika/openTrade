"""Binance live kline stream → StreamEvent async iterator."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import AsyncIterator

from binance import AsyncClient, BinanceSocketManager

from backend.market.data_sources.binance_loader import (
    INTERVAL_MAP,
    _normalize_binance_symbol,
)
from backend.market.models import OHLCVCandle
from backend.streaming.protocol import StreamEvent

logger = logging.getLogger(__name__)


def _kline_to_event(msg: dict, symbol: str, interval: str) -> StreamEvent | None:
    """Translate one Binance kline payload to a StreamEvent.

    Returns None if the message isn't a kline payload (e.g. error or pong).
    """
    k = msg.get("k")
    if not k:
        return None
    open_ms = int(k["t"])
    candle = OHLCVCandle(
        symbol=symbol,
        timestamp=datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc).replace(
            tzinfo=None
        ),
        open=float(k["o"]),
        high=float(k["h"]),
        low=float(k["l"]),
        close=float(k["c"]),
        volume=float(k["v"]),
    )
    is_final = bool(k.get("x", False))
    return StreamEvent(
        kind="candle_close" if is_final else "candle_update",
        symbol=symbol,
        interval=interval,
        candle=candle,
        is_final=is_final,
    )


async def stream_binance_klines(
    symbol: str, interval: str
) -> AsyncIterator[StreamEvent]:
    """Yield live StreamEvents from Binance's kline WebSocket.

    Public (unauthenticated) connection — sufficient for read-only market data.
    Caller is responsible for cancellation; on cancel we tear down the
    AsyncClient cleanly.
    """
    sym_norm = _normalize_binance_symbol(symbol)
    bi_interval = INTERVAL_MAP.get(interval)
    if bi_interval is None:
        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported: {', '.join(sorted(INTERVAL_MAP))}"
        )

    client = await AsyncClient.create()
    try:
        bm = BinanceSocketManager(client)
        async with bm.kline_socket(symbol=sym_norm, interval=bi_interval) as stream:
            while True:
                msg = await stream.recv()
                event = _kline_to_event(msg, symbol=sym_norm, interval=interval)
                if event is not None:
                    yield event
    finally:
        await client.close_connection()
