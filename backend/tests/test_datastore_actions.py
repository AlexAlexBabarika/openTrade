from datetime import datetime, timezone
from backend.market.models import CorporateAction
from pathlib import Path
from backend.datastore.actions import actions_to_frame, read_actions, write_actions
from backend.datastore.layout import StoreLayout
from backend.datastore.schema import ACTIONS_SCHEMA


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


def test_actions_to_frame_schema():
    f = actions_to_frame(
        [
            CorporateAction(
                symbol="AAPL",
                ex_date=datetime(2020, 8, 31, tzinfo=timezone.utc),
                kind="split",
                value=4.0,
            ),
        ]
    )
    assert dict(f.schema) == ACTIONS_SCHEMA
    assert f.height == 1


def test_actions_to_frame_empty():
    f = actions_to_frame([])
    assert dict(f.schema) == ACTIONS_SCHEMA
    assert f.height == 0


def test_write_read_roundtrip(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    f = actions_to_frame(
        [
            CorporateAction(
                symbol="AAPL",
                ex_date=datetime(2020, 8, 31, tzinfo=timezone.utc),
                kind="split",
                value=4.0,
            ),
        ]
    )
    write_actions(layout, "yfinance", "AAPL", f)
    back = read_actions(layout, "yfinance", "AAPL")
    assert back.height == 1
    assert back["value"].to_list() == [4.0]


def test_read_missing_returns_empty(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    assert read_actions(layout, "yfinance", "NOPE").height == 0
