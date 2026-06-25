from datetime import datetime, timezone
from pathlib import Path

from backend.datastore.ingest import ingest_symbols
from backend.datastore.layout import StoreLayout
from backend.datastore.manifest import load_manifest
from backend.market.models import CorporateAction, OHLCVCandle


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


class FakeProvider:
    """Duck-typed provider: raw bars + actions, deterministic, no network."""

    name = "fake"

    def __init__(self, bars: dict, actions: dict):
        self._bars = bars
        self._actions = actions

    def get_raw_ohlcv(self, symbol, period="max", interval="1d"):
        return self._bars[symbol]

    def get_corporate_actions(self, symbol):
        return self._actions.get(symbol, [])


def _candle(t, c, symbol="X"):
    return OHLCVCandle(
        symbol=symbol, timestamp=t, open=c, high=c, low=c, close=c, volume=100.0
    )


def test_ingest_writes_bars_actions_and_manifest(tmp_path: Path):
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
    report = ingest_symbols(layout, provider, ["AAPL"], period="max", interval="1d")

    assert layout.bars("fake", "AAPL").exists()
    assert layout.actions("fake", "AAPL").exists()
    assert report.rows_written["AAPL"] == 2
    manifest = load_manifest(layout)
    assert manifest["head"] == report.data_version
    assert "AAPL" in manifest["versions"][report.data_version]["symbols"]


def test_ingest_quarantines_bad_bars(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    bad = OHLCVCandle(
        symbol="X",
        timestamp=_utc(2020, 1, 2),
        open=10,
        high=8,
        low=9,
        close=10,
        volume=1.0,
    )
    provider = FakeProvider(
        bars={"X": [_candle(_utc(2020, 1, 1), 10.0), bad]},
        actions={},
    )
    report = ingest_symbols(layout, provider, ["X"], period="max", interval="1d")
    assert report.quarantined["X"] == 1
    assert layout.quarantine("fake", "X").exists()


def test_ingest_seeds_membership_when_indices_given(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    provider = FakeProvider(bars={"AAPL": [_candle(_utc(2020, 1, 1), 1.0)]}, actions={})
    ingest_symbols(
        layout, provider, ["AAPL"], period="max", interval="1d", indices=["SP500"]
    )
    assert layout.membership("SP500").exists()
