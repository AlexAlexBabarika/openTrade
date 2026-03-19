"""Binance market data provider using python-binance."""

import logging
from datetime import datetime, timezone

from binance.client import Client

from backend.market.data_sources.marketdataprovider import MarketDataProvider
from backend.market.models import OHLCVCandle
from backend.market.time_utils import period_to_startdate

# from backend.core.api_key_store import fetch_api_key

logger = logging.getLogger(__name__)

INTERVAL_MAP: dict[str, str] = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE,
    "30m": Client.KLINE_INTERVAL_30MINUTE,
    "1h": Client.KLINE_INTERVAL_1HOUR,
    "4h": Client.KLINE_INTERVAL_4HOUR,
    "1d": Client.KLINE_INTERVAL_1DAY,
    "1w": Client.KLINE_INTERVAL_1WEEK,
    "1mo": Client.KLINE_INTERVAL_1MONTH,
}


def _parse_kline(kline: list, symbol: str) -> OHLCVCandle:
    """Convert a raw Binance kline array to OHLCVCandle.

    Kline format: [open_time, open, high, low, close, volume, close_time, ...]
    """
    open_time_ms = int(kline[0])
    return OHLCVCandle(
        symbol=symbol,
        timestamp=datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).replace(
            tzinfo=None
        ),
        open=float(kline[1]),
        high=float(kline[2]),
        low=float(kline[3]),
        close=float(kline[4]),
        volume=float(kline[5]),
    )


class BinanceProvider(MarketDataProvider):
    """Fetches OHLCV klines from Binance.

    Accepts an optional user_id. When provided, the user's stored API
    key/secret pair is used (format: ``key:secret``). When omitted,
    unauthenticated public access is used (lower rate limits).
    """

    def __init__(self, user_id: str | None = None) -> None:
        self._user_id = user_id

    @property
    def name(self) -> str:
        return "binance"

    @property
    def requires_api_key(self) -> bool:
        return False

    # def _make_client(self) -> Client:
    #     if self._user_id:
    #         try:
    #             raw = fetch_api_key(self._user_id, "binance")
    #             if ":" in raw:
    #                 api_key, api_secret = raw.split(":", 1)
    #             else:
    #                 api_key, api_secret = raw, ""
    #             return Client(api_key, api_secret)
    #         except ValueError:
    #             logger.debug(
    #                 "No Binance API key for user %s, using public access",
    #                 self._user_id,
    #             )
    #     return Client()

    def get_ohlcv(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[OHLCVCandle]:
        bi_interval = INTERVAL_MAP.get(interval)
        if bi_interval is None:
            raise ValueError(
                f"Unsupported interval '{interval}'. "
                f"Supported: {', '.join(sorted(INTERVAL_MAP))}"
            )
        start_date = period_to_startdate(period)
        # client = self._make_client()
        client = Client()
        klines = client.get_historical_klines(
            symbol.upper(),
            bi_interval,
            start_date,
        )
        if not klines:
            return []
        return [_parse_kline(k, symbol) for k in klines]


_provider = BinanceProvider()


def load_binance(
    symbol: str, period: str = "1mo", interval: str = "1d"
) -> list[OHLCVCandle]:
    """Convenience function for unauthenticated Binance access."""
    return _provider.get_ohlcv(symbol, period, interval)
