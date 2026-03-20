"""Twelve Data API provider."""

import logging

import requests

from backend.market.data_sources.marketdataprovider import MarketDataProvider
from backend.market.models import OHLCVCandle
from backend.market.normalizer import normalize_rows
from backend.market.shared_config import resolve_twelvedata_interval
from backend.market.time_utils import period_to_startdate
from backend.core.api_key_store import fetch_api_key

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.twelvedata.com/time_series"


class TwelveDataProvider(MarketDataProvider):
    def __init__(self, user_id: str) -> None:
        self._user_id = user_id

    @property
    def name(self) -> str:
        return "twelvedata"

    @property
    def requires_api_key(self) -> bool:
        return True

    def get_ohlcv(
        self, symbol: str, period: str = "1mo", interval: str = "1day"
    ) -> list[OHLCVCandle]:
        api_key = fetch_api_key(self._user_id, "twelvedata").strip()
        start_date = period_to_startdate(period)
        td_interval = resolve_twelvedata_interval(interval)
        resp = requests.get(
            _BASE_URL,
            params={
                "symbol": symbol.strip(),
                "interval": td_interval,
                "start_date": start_date,
                "apikey": api_key,
                "timezone": "UTC",
                "order": "asc",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "error":
            raise RuntimeError(
                f"Twelve Data API error: {data.get('message', 'unknown')}"
            )
        values = data.get("values")
        if not values:
            return []
        return normalize_rows(values, symbol)
