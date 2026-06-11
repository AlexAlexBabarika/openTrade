# backend/tests/test_portfolio_routes.py
"""The /portfolio-backtests API: a sandboxed multi-asset run of strategy code.

Market data is stubbed per symbol so the test is hermetic (no provider calls).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
import pytest
from fastapi.testclient import TestClient

import backend.routes.portfolio_routes as portfolio_routes
from backend.app import app

CODE = (
    "def on_bar(ctx):\n"
    "    for symbol, weight in equal_weight(ctx.universe).items():\n"
    "        ctx.target_weight(symbol, weight)\n"
    "    if ctx.time.day == 1:\n"
    "        ctx.rebalance()\n"
)


@pytest.fixture(autouse=True)
def _stub_frames(monkeypatch) -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)

    async def _fake_load_frame(body):
        n = 30
        ts = [start + timedelta(days=i) for i in range(n)]
        seed = sum(ord(c) for c in body.symbol)
        close = 100 + np.cumsum(np.random.default_rng(seed).standard_normal(n) * 0.5)
        frame = pl.DataFrame(
            {
                "timestamp": ts,
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.full(n, 1e6),
            }
        ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))
        return frame, f"stub:{body.symbol}"

    monkeypatch.setattr(portfolio_routes, "_load_frame", _fake_load_frame)


client = TestClient(app)


def _run(payload_overrides: dict | None = None) -> dict:
    payload = {
        "code": CODE,
        "symbols": ["MSFT", "AAPL"],
        "provider": "yfinance",
    }
    payload.update(payload_overrides or {})
    r = client.post("/portfolio-backtests/run", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_run_returns_the_full_portfolio_blob() -> None:
    body = _run()
    assert body["status"] == "ok", body["stderr"]
    for key in (
        "meta",
        "symbols",
        "bars",
        "orders",
        "fills",
        "equity",
        "trades",
        "constraint_events",
        "metrics",
    ):
        assert key in body
    assert body["symbols"] == ["AAPL", "MSFT"]  # deduped + sorted
    assert len(body["equity"]) == 30
    assert {f["symbol"] for f in body["fills"]} == {"AAPL", "MSFT"}
    assert "sharpe" in body["metrics"]["portfolio"]


def test_run_enforces_request_constraints() -> None:
    body = _run({"constraints": {"max_position_weight": 0.1}})
    assert body["status"] == "ok", body["stderr"]
    assert any(
        e["constraint"] == "max_position_weight" for e in body["constraint_events"]
    )


def test_invalid_code_is_a_400() -> None:
    r = client.post(
        "/portfolio-backtests/run",
        json={"code": "import os", "symbols": ["AAPL"], "provider": "yfinance"},
    )
    assert r.status_code == 400


def test_too_many_symbols_is_a_422() -> None:
    r = client.post(
        "/portfolio-backtests/run",
        json={
            "code": CODE,
            "symbols": [f"S{i}" for i in range(51)],
            "provider": "yfinance",
        },
    )
    assert r.status_code == 422
