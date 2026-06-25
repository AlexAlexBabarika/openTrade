"""CRUD round-trip tests for /strategies (saved backtest strategies).

Reuses the in-memory postgrest shim from test_script_crud; only the route
module and table differ.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

import pytest

from backend.app import app
from backend.core.auth_deps import get_current_user, optional_current_user
from backend.models.auth_models import AuthUserInfo
from backend.routes import strategy_routes
from backend.tests.test_script_crud import _FakeDB

USER_A = AuthUserInfo(id="11111111-1111-1111-1111-111111111111", email="a@x.com")
USER_B = AuthUserInfo(id="22222222-2222-2222-2222-222222222222", email="b@x.com")

CODE = "params = {}\n\ndef on_bar(ctx):\n    pass\n"


@pytest.fixture
def fake_db(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(strategy_routes, "get_service_postgrest", lambda: db)
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
    r = client.post("/strategies", json={"name": "buyhold", "code": CODE})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert r.json()["name"] == "buyhold"

    r = client.get("/strategies")
    assert r.status_code == 200
    assert [s["id"] for s in r.json()["strategies"]] == [sid]

    r = client.get(f"/strategies/{sid}")
    assert r.status_code == 200
    assert r.json()["code"] == CODE

    r = client.put(f"/strategies/{sid}", json={"code": "y = 2"})
    assert r.status_code == 200
    assert r.json()["code"] == "y = 2"
    assert r.json()["name"] == "buyhold"

    r = client.delete(f"/strategies/{sid}")
    assert r.status_code == 204

    r = client.get(f"/strategies/{sid}")
    assert r.status_code == 404


def test_update_requires_a_field(fake_db, auth_user_a, client):
    r = client.post("/strategies", json={"name": "s", "code": CODE})
    sid = r.json()["id"]
    r = client.put(f"/strategies/{sid}", json={})
    assert r.status_code == 400


def test_duplicate_name_conflict(fake_db, auth_user_a, client):
    assert (
        client.post("/strategies", json={"name": "dup", "code": "a"}).status_code == 201
    )
    r = client.post("/strategies", json={"name": "dup", "code": "b"})
    assert r.status_code == 409


def test_strategies_do_not_collide_with_scripts_table(fake_db, auth_user_a, client):
    r = client.post("/strategies", json={"name": "x", "code": CODE})
    assert r.status_code == 201
    assert "user_strategies" in fake_db.tables
    assert "user_scripts" not in fake_db.tables


def test_other_user_cannot_access(fake_db, auth_user_a, client):
    r = client.post("/strategies", json={"name": "mine", "code": "a"})
    sid = r.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: USER_B
    try:
        assert client.get(f"/strategies/{sid}").status_code == 404
        assert client.put(f"/strategies/{sid}", json={"code": "z"}).status_code == 404
        assert client.delete(f"/strategies/{sid}").status_code == 404
        assert client.get("/strategies").json()["strategies"] == []
    finally:
        app.dependency_overrides[get_current_user] = lambda: USER_A
