"""
The DB is faked with a tiny in-memory fluent shim that mimics the postgrest
calls actually used by `script_routes` — enough for round-tripping without
spinning up Supabase.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.core.auth_deps import get_current_user, optional_current_user
from backend.models.auth_models import AuthUserInfo
from backend.market.models import OHLCVCandle
from backend.routes import script_routes


USER_A = AuthUserInfo(id="11111111-1111-1111-1111-111111111111", email="a@x.com")
USER_B = AuthUserInfo(id="22222222-2222-2222-2222-222222222222", email="b@x.com")


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table: "_Table", op: str, payload=None):
        self.table = table
        self.op = op
        self.payload = payload
        self.filters: dict[str, object] = {}
        self.order_by: tuple[str, bool] | None = None
        self._limit: int | None = None

    def eq(self, col, val):
        self.filters[col] = val
        return self

    def order(self, col, desc=False):
        self.order_by = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def select(self, *_args, **_kwargs):
        # `.delete().select("id")` returns deleted rows; otherwise no-op.
        return self

    def _matches(self, row: dict) -> bool:
        return all(row.get(k) == v for k, v in self.filters.items())

    def execute(self) -> _Resp:
        rows = self.table.rows
        if self.op == "select":
            out = [r for r in rows if self._matches(r)]
            if self.order_by:
                col, desc = self.order_by
                out.sort(key=lambda r: r.get(col) or "", reverse=desc)
            if self._limit is not None:
                out = out[: self._limit]
            return _Resp([dict(r) for r in out])
        if self.op == "insert":
            now = datetime.now(timezone.utc).isoformat()
            inserted = []
            payload = self.payload if isinstance(self.payload, list) else [self.payload]
            for p in payload:
                # Enforce the unique (user_id, name) constraint the migration declares.
                if any(
                    r["user_id"] == p["user_id"] and r["name"] == p["name"]
                    for r in rows
                ):
                    from postgrest.exceptions import APIError

                    raise APIError(
                        {"code": "23505", "message": "duplicate key", "hint": ""}
                    )
                row = {
                    "id": str(uuid.uuid4()),
                    "created_at": now,
                    "updated_at": now,
                    **p,
                }
                rows.append(row)
                inserted.append(dict(row))
            return _Resp(inserted)
        if self.op == "update":
            now = datetime.now(timezone.utc).isoformat()
            updated = []
            for r in rows:
                if self._matches(r):
                    r.update(self.payload)
                    r["updated_at"] = now
                    updated.append(dict(r))
            return _Resp(updated)
        if self.op == "delete":
            kept, removed = [], []
            for r in rows:
                if self._matches(r):
                    removed.append(dict(r))
                else:
                    kept.append(r)
            self.table.rows = kept
            return _Resp(removed)
        raise AssertionError(f"unsupported op: {self.op}")


class _Table:
    def __init__(self):
        self.rows: list[dict] = []

    def select(self, *_args, **_kwargs):
        return _Query(self, "select")

    def insert(self, payload):
        return _Query(self, "insert", payload)

    def update(self, payload):
        return _Query(self, "update", payload)

    def delete(self):
        return _Query(self, "delete")


class _FakeDB:
    def __init__(self):
        self.tables: dict[str, _Table] = {}

    def from_(self, name: str) -> _Table:
        return self.tables.setdefault(name, _Table())


@pytest.fixture
def fake_db(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(script_routes, "get_service_postgrest", lambda: db)
    return db


@pytest.fixture
def auth_user_a():
    app.dependency_overrides[get_current_user] = lambda: USER_A
    app.dependency_overrides[optional_current_user] = lambda: USER_A
    yield USER_A
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(optional_current_user, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_create_list_get_update_delete(fake_db, auth_user_a, client):
    r = client.post("/scripts", json={"name": "sma20", "code": "x = 1"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert r.json()["name"] == "sma20"

    r = client.get("/scripts")
    assert r.status_code == 200
    assert [s["id"] for s in r.json()["scripts"]] == [sid]

    r = client.get(f"/scripts/{sid}")
    assert r.status_code == 200
    assert r.json()["code"] == "x = 1"

    r = client.put(f"/scripts/{sid}", json={"code": "y = 2"})
    assert r.status_code == 200
    assert r.json()["code"] == "y = 2"
    assert r.json()["name"] == "sma20"

    r = client.delete(f"/scripts/{sid}")
    assert r.status_code == 204

    r = client.get(f"/scripts/{sid}")
    assert r.status_code == 404


def test_duplicate_name_conflict(fake_db, auth_user_a, client):
    assert client.post("/scripts", json={"name": "dup", "code": "a"}).status_code == 201
    r = client.post("/scripts", json={"name": "dup", "code": "b"})
    assert r.status_code == 409


def test_other_user_cannot_access(fake_db, auth_user_a, client):
    r = client.post("/scripts", json={"name": "mine", "code": "a"})
    sid = r.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: USER_B
    try:
        assert client.get(f"/scripts/{sid}").status_code == 404
        assert client.put(f"/scripts/{sid}", json={"code": "z"}).status_code == 404
        assert client.delete(f"/scripts/{sid}").status_code == 404
        assert client.get("/scripts").json()["scripts"] == []
    finally:
        app.dependency_overrides[get_current_user] = lambda: USER_A


def test_execute_by_script_id_round_trip(fake_db, auth_user_a, client, monkeypatch):
    code = "display.line(price.rolling_mean(3), title='SMA3')"
    r = client.post("/scripts", json={"name": "sma3", "code": code})
    assert r.status_code == 201
    sid = r.json()["id"]

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    timestamps = [start + timedelta(days=i) for i in range(10)]
    closes = np.linspace(100.0, 110.0, 10)
    candles = [
        OHLCVCandle(
            symbol="TEST",
            timestamp=ts,
            open=float(c),
            high=float(c) + 1,
            low=float(c) - 1,
            close=float(c),
            volume=1000.0,
        )
        for ts, c in zip(timestamps, closes)
    ]
    monkeypatch.setattr(script_routes.cache, "get_cached", lambda *a, **kw: candles)

    r = client.post(
        "/scripts/execute",
        json={
            "script_id": sid,
            "symbol": "TEST",
            "provider": "yfinance",
            "period": "1mo",
            "interval": "1d",
            "timeout_s": 10.0,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok", body
    assert body["outputs"] and body["outputs"][0]["type"] == "overlay"
    assert body["outputs"][0]["title"] == "SMA3"


def test_execute_unknown_script_id_404(fake_db, auth_user_a, client):
    r = client.post(
        "/scripts/execute",
        json={
            "script_id": "00000000-0000-0000-0000-000000000000",
            "symbol": "TEST",
            "provider": "yfinance",
        },
    )
    assert r.status_code == 404


def test_execute_requires_code_or_script_id(fake_db, auth_user_a, client):
    r = client.post(
        "/scripts/execute",
        json={"symbol": "TEST", "provider": "yfinance"},
    )
    assert r.status_code == 400
