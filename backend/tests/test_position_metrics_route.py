"""Route tests for POST /data/position-metrics."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_post_long_ok():
    r = client.post(
        "/data/position-metrics",
        json={
            "side": "long",
            "entryPrice": 100,
            "stopPrice": 95,
            "targetPrice": 110,
        },
    )
    assert r.status_code == 200
    assert r.json() == {"riskRewardRatio": 2.0}


def test_post_invalid_long_levels_422():
    r = client.post(
        "/data/position-metrics",
        json={
            "side": "long",
            "entryPrice": 100,
            "stopPrice": 101,
            "targetPrice": 110,
        },
    )
    assert r.status_code == 422
