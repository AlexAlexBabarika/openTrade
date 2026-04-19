"""Route smoke tests for /data/volume-profile."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.market import cache
from backend.market.models import OHLCVCandle

client = TestClient(app)


def _candle(
    ts: datetime, o: float, h: float, lo: float, c: float, v: float
) -> OHLCVCandle:
    return OHLCVCandle(
        timestamp=ts,
        symbol="TEST",
        open=o,
        high=h,
        low=lo,
        close=c,
        volume=v,
    )


@pytest.fixture(autouse=True)
def _reset_caches():
    cache.clear_profile_cache()
    # Remove only our test symbol to avoid stepping on other tests' fixtures.
    from backend.market.cache import _data_cache  # type: ignore

    _data_cache.pop("yahoo:TEST", None)
    yield
    _data_cache.pop("yahoo:TEST", None)
    cache.clear_profile_cache()


def test_404_when_no_candles_cached():
    r = client.get(
        "/data/volume-profile",
        params={
            "provider": "yahoo",
            "symbol": "TEST",
            "startTs": 0,
            "rowSize": 1.0,
            "interval": "1d",
        },
    )
    assert r.status_code == 404


def test_200_with_expected_shape():
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles = [
        _candle(
            base + timedelta(days=i), 10 + i, 12 + i, 9 + i, 11 + i, 100.0 * (i + 1)
        )
        for i in range(5)
    ]
    cache.set_cached("yahoo", "TEST", candles)
    start_ts = int(base.timestamp())

    r = client.get(
        "/data/volume-profile",
        params={
            "provider": "yahoo",
            "symbol": "TEST",
            "startTs": start_ts,
            "rowSize": 1.0,
            "vaPercent": 0.7,
            "interval": "1d",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "candle-distribution"
    assert "bins" in body and len(body["bins"]) > 0
    assert body["val"] <= body["poc"] <= body["vah"]
    b0 = body["bins"][0]
    assert {"price", "upVol", "downVol"} <= set(b0.keys())


def test_cache_hit_second_call_returns_same_payload():
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles = [_candle(base, 10, 12, 9, 11, 100.0)]
    cache.set_cached("yahoo", "TEST", candles)

    params = {
        "provider": "yahoo",
        "symbol": "TEST",
        "startTs": int(base.timestamp()),
        "rowSize": 1.0,
        "vaPercent": 0.7,
        "interval": "1d",
    }
    first = client.get("/data/volume-profile", params=params).json()
    second = client.get("/data/volume-profile", params=params).json()
    assert first == second
