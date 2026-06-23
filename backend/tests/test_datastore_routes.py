# backend/tests/test_datastore_routes.py
"""The /datastore/ingest API: the explicit store-population step.

Each test points the route's module-level handles at a tmp store and a
deterministic fake provider (no network), then asserts the ingest report and
that bars land on disk for a subsequent read.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.routes.datastore_routes as datastore_routes
from backend.app import app
from backend.market.models import OHLCVCandle

_START = datetime(2020, 8, 15, tzinfo=timezone.utc)
_DAYS = [_START + timedelta(days=i) for i in range(10)]


def _candle(t, c, symbol):
    return OHLCVCandle(
        symbol=symbol,
        timestamp=t,
        open=c,
        high=c + 0.5,
        low=c - 0.5,
        close=c,
        volume=1e6,
    )


class _FakeProvider:
    name = "yfinance"

    def get_raw_ohlcv(self, symbol, period="max", interval="1d"):
        return [_candle(t, 100.0, symbol) for t in _DAYS]

    def get_corporate_actions(self, symbol):
        return []


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path: Path, monkeypatch):
    from backend.datastore.layout import StoreLayout

    monkeypatch.setattr(datastore_routes, "_STORE_LAYOUT", StoreLayout(root=tmp_path))
    monkeypatch.setattr(datastore_routes, "_provider", _FakeProvider)
    return tmp_path


client = TestClient(app)


def test_ingest_writes_bars_and_returns_report(_tmp_store: Path):
    r = client.post("/datastore/ingest", json={"symbols": ["AAPL", "MSFT"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data_version"]
    assert body["rows_written"] == {"AAPL": 10, "MSFT": 10}
    assert (_tmp_store / "bars" / "yfinance" / "AAPL.parquet").exists()


def test_ingest_dedupes_and_strips_symbols():
    r = client.post("/datastore/ingest", json={"symbols": ["aapl ", " AAPL"]})
    assert r.status_code == 200, r.text
    # "aapl" and "AAPL" are distinct strings; only whitespace is stripped.
    assert set(r.json()["rows_written"]) == {"aapl", "AAPL"}


def test_empty_symbols_is_a_422():
    r = client.post("/datastore/ingest", json={"symbols": []})
    assert r.status_code == 422


def test_too_many_symbols_is_a_422():
    r = client.post("/datastore/ingest", json={"symbols": [f"S{i}" for i in range(51)]})
    assert r.status_code == 422
