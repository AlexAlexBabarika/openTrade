from datetime import datetime, timezone

from backend.market.models import CorporateAction


def test_corporate_action_model():
    ca = CorporateAction(
        symbol="AAPL",
        ex_date=datetime(2020, 8, 31, tzinfo=timezone.utc),
        kind="split",
        value=4.0,
    )
    assert ca.kind == "split"
    assert ca.value == 4.0


def test_provider_abc_default_raises():
    from backend.market.data_sources.marketdataprovider import MarketDataProvider

    class Bare(MarketDataProvider):
        name = "bare"
        requires_api_key = False

        def get_ohlcv(self, symbol, period="1mo", interval="1d"):
            return []

    import pytest

    with pytest.raises(NotImplementedError):
        Bare().get_corporate_actions("AAPL")
