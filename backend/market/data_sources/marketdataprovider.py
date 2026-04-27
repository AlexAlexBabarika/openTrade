from abc import ABC, abstractmethod
from typing import AsyncIterator, TYPE_CHECKING

from backend.market.models import OHLCVCandle
from backend.models.market_data_models import SymbolRecord

if TYPE_CHECKING:
    from backend.streaming.protocol import StreamEvent


class MarketDataProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the data source."""
        ...

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether the data source requires an API key."""
        ...

    @abstractmethod
    def get_ohlcv(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> list[OHLCVCandle]:
        """Get OHLCV candles for a given symbol and period."""
        ...

    def list_symbols(self) -> list[SymbolRecord]:
        """Enumerate all symbols this provider supports. Optional."""
        raise NotImplementedError

    def supports_streaming(self) -> bool:
        """Whether the provider can stream live OHLCV via stream_ohlcv()."""
        return False

    def stream_ohlcv(self, symbol: str, interval: str) -> AsyncIterator["StreamEvent"]:
        """Async iterator yielding live StreamEvents. Optional."""
        raise NotImplementedError
