from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.datastore.errors import DataNotFound
from backend.datastore.ingest import ingest_symbols
from backend.datastore.layout import StoreLayout
from backend.datastore.store import HistoricalStore
from backend.market.models import CorporateAction, OHLCVCandle


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


class FakeProvider:
    name = "fake"

    def __init__(self, bars, actions):
        self._bars, self._actions = bars, actions

    def get_raw_ohlcv(self, symbol, period="max", interval="1d"):
        return self._bars[symbol]

    def get_corporate_actions(self, symbol):
        return self._actions.get(symbol, [])


def _candle(t, c, v=100.0, symbol="AAPL"):
    return OHLCVCandle(
        symbol=symbol, timestamp=t, open=c, high=c, low=c, close=c, volume=v
    )


@pytest.fixture
def store(tmp_path: Path) -> HistoricalStore:
    layout = StoreLayout(root=tmp_path)
    provider = FakeProvider(
        bars={
            "AAPL": [
                _candle(_utc(2020, 8, 28), 500.0),
                _candle(_utc(2020, 8, 31), 125.0),
            ]
        },
        actions={
            "AAPL": [
                CorporateAction(
                    symbol="AAPL", ex_date=_utc(2020, 8, 31), kind="split", value=4.0
                )
            ]
        },
    )
    ingest_symbols(layout, provider, ["AAPL"], indices=["SP500"])
    return HistoricalStore(layout, provider_name="fake")


def test_read_frames_is_back_adjusted_with_raw_retained(store):
    frames = store.read_frames(["AAPL"])
    f = frames["AAPL"]
    assert f["close"].to_list() == [125.0, 125.0]  # continuous (AC#2)
    assert f["raw_close"].to_list() == [500.0, 125.0]  # raw retained for fills


def test_read_frames_deterministic(store):
    a = store.read_frames(["AAPL"])["AAPL"]
    b = store.read_frames(["AAPL"])["AAPL"]
    assert a.equals(b)  # same data_version -> identical (AC#3)


def test_missing_symbol_raises(store):
    with pytest.raises(DataNotFound):
        store.read_frames(["NOPE"])


def test_resolve_universe(store):
    u = store.resolve_universe("SP500", _utc(2026, 6, 1), _utc(2026, 6, 2))
    assert "AAPL" in u.symbols


def test_head_version_present(store):
    assert store.head_version()
