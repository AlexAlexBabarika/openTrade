"""Route tests for /data/analytics/*.

Cache is seeded directly via backend.market.cache so tests don't depend
on external data sources.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.market import cache
from backend.tests._analytics_helpers import make_candles

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache._data_cache.clear()
    cache._csv_keys.clear()
    yield
    cache._data_cache.clear()
    cache._csv_keys.clear()


def _seed(symbol: str, closes: list[float]) -> None:
    cache.set_cached("yfinance", symbol, make_candles(closes))


# --- 404 cache miss ---------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/data/analytics/sharpe",
        "/data/analytics/sortino",
        "/data/analytics/max_drawdown",
        "/data/analytics/var",
        "/data/analytics/variance",
        "/data/analytics/stdev",
        "/data/analytics/skewness",
        "/data/analytics/kurtosis",
        "/data/analytics/volatility_clustering",
        "/data/analytics/hurst",
        "/data/analytics/return_distribution",
    ],
)
def test_cache_miss_returns_404(path: str):
    r = client.get(path, params={"symbol": "MISSING"})
    assert r.status_code == 404


def test_correlation_cache_miss_returns_404():
    r = client.get("/data/analytics/correlation", params={"symbol": "MISSING"})
    assert r.status_code == 404


# --- Happy paths ------------------------------------------------------------


def test_variance_ok():
    _seed("AAPL", [1.0, 2.0, 3.0, 4.0, 5.0])
    r = client.get("/data/analytics/variance", params={"symbol": "AAPL"})
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "AAPL"
    assert body["metric"] == "variance"
    assert body["n"] == 4
    assert isinstance(body["value"], float)


def test_stdev_ok():
    _seed("AAPL", [1.0, 2.0, 3.0, 4.0, 5.0])
    r = client.get("/data/analytics/stdev", params={"symbol": "AAPL"})
    assert r.status_code == 200
    assert r.json()["metric"] == "stdev"


def test_sharpe_ok():
    rng = np.random.default_rng(42)
    closes = list(np.cumprod(1.0 + rng.normal(0.0005, 0.01, 300)) * 100.0)
    _seed("AAPL", closes)
    r = client.get("/data/analytics/sharpe", params={"symbol": "AAPL"})
    assert r.status_code == 200
    body = r.json()
    assert body["metric"] == "sharpe"
    assert math.isfinite(body["value"])


def test_max_drawdown_ok():
    _seed("AAPL", [100.0, 110.0, 90.0, 95.0])
    r = client.get("/data/analytics/max_drawdown", params={"symbol": "AAPL"})
    assert r.status_code == 200
    body = r.json()
    assert body["metric"] == "max_drawdown"
    assert body["max_drawdown"] < 0
    assert len(body["series"]) == 4


def test_var_ok():
    rng = np.random.default_rng(0)
    closes = list(np.cumprod(1.0 + rng.normal(0.0, 0.01, 200)) * 100.0)
    _seed("AAPL", closes)
    r = client.get("/data/analytics/var", params={"symbol": "AAPL"})
    assert r.status_code == 200
    body = r.json()
    assert body["var_95"] <= body["var_99"] or body["var_99"] <= body["var_95"]
    assert body["n"] == 199


def test_return_distribution_ok():
    _seed("AAPL", [float(i + 1) for i in range(20)])
    r = client.get(
        "/data/analytics/return_distribution",
        params={"symbol": "AAPL", "bins": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["bins"]) == 5
    assert sum(b["count"] for b in body["bins"]) == 19


def test_volatility_clustering_ok():
    rng = np.random.default_rng(1)
    closes = list(np.cumprod(1.0 + rng.normal(0.0, 0.01, 300)) * 100.0)
    _seed("AAPL", closes)
    r = client.get(
        "/data/analytics/volatility_clustering",
        params={"symbol": "AAPL", "lag": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["lag"] == 5
    assert math.isfinite(body["q"])


def test_hurst_ok():
    rng = np.random.default_rng(7)
    # random walk → enough length for the 100-return floor
    closes = list(np.cumprod(1.0 + rng.normal(0.0, 0.01, 500)) * 100.0)
    _seed("AAPL", closes)
    r = client.get("/data/analytics/hurst", params={"symbol": "AAPL"})
    assert r.status_code == 200
    assert math.isfinite(r.json()["value"])


def test_correlation_ok():
    rng = np.random.default_rng(3)
    base = list(np.cumprod(1.0 + rng.normal(0.0, 0.01, 200)) * 100.0)
    _seed("AAPL", base)
    _seed("SPY", base)  # perfectly correlated copy → ρ ≈ 1
    r = client.get(
        "/data/analytics/correlation",
        params={"symbol": "AAPL", "benchmarks": "SPY"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rows"][0]["benchmark"] == "SPY"
    assert body["rows"][0]["value"] == pytest.approx(1.0, abs=1e-6)


def test_correlation_missing_benchmark_404():
    _seed("AAPL", [100.0, 101.0, 102.0])
    r = client.get(
        "/data/analytics/correlation",
        params={"symbol": "AAPL", "benchmarks": "NOPE"},
    )
    assert r.status_code == 404


# --- 400 invalid input ------------------------------------------------------


def test_volatility_clustering_invalid_lag_422():
    _seed("AAPL", [100.0, 101.0])
    r = client.get(
        "/data/analytics/volatility_clustering",
        params={"symbol": "AAPL", "lag": 0},
    )
    # FastAPI Query(ge=1) → 422 on validation
    assert r.status_code == 422


def test_hurst_too_few_returns_400():
    _seed("AAPL", [100.0, 101.0, 102.0])
    r = client.get("/data/analytics/hurst", params={"symbol": "AAPL"})
    assert r.status_code == 400
