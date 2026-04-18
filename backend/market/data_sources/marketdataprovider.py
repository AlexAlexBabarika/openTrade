from abc import ABC, abstractmethod

from backend.market.models import OHLCVCandle
from backend.models.market_data_models import SymbolRecord


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
