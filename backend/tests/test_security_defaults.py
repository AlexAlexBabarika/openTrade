from io import BytesIO

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from starlette.responses import Response
from starlette.websockets import WebSocketDisconnect

from backend.app import app
from backend.core.config import security_settings
from backend.core.uploads import read_upload
from backend.routes.auth_routes import _set_refresh_cookie


@pytest.fixture(autouse=True)
def reset_settings():
    security_settings.cache_clear()
    yield
    security_settings.cache_clear()


def test_default_is_same_origin_only(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert security_settings().cors_origins == ()


def test_wildcard_cors_is_rejected(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="explicit origins"):
        security_settings()


def test_wildcard_host_is_rejected(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "*")
    with pytest.raises(RuntimeError, match="explicit hostnames"):
        security_settings()


def test_cross_site_cookie_configuration_requires_https(monkeypatch):
    monkeypatch.setenv("COOKIE_SAMESITE", "none")
    monkeypatch.setenv("COOKIE_SECURE", "0")
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        security_settings()


def test_non_positive_resource_limit_is_rejected(monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_SWEEPS", "0")
    with pytest.raises(RuntimeError, match="greater than zero"):
        security_settings()


def test_request_limit_cannot_be_smaller_than_upload_limit(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10")
    monkeypatch.setenv("MAX_REQUEST_BYTES", "9")
    with pytest.raises(RuntimeError, match="at least"):
        security_settings()


def test_refresh_cookie_has_safe_default_attributes(monkeypatch):
    monkeypatch.delenv("COOKIE_SAMESITE", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    response = Response()
    _set_refresh_cookie(response, "secret")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/auth" in cookie


@pytest.mark.asyncio
async def test_upload_limit_is_enforced(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "4")
    file = UploadFile(filename="large.csv", file=BytesIO(b"12345"))
    with pytest.raises(Exception) as exc_info:
        await read_upload(file)
    assert exc_info.value.status_code == 413


def test_cross_origin_websocket_is_rejected():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/live", headers={"origin": "https://attacker.example"}
        ):
            pass
    assert exc_info.value.code == 1008


def test_oversized_http_request_is_rejected_before_routing():
    response = TestClient(app).post(
        "/auth/login",
        headers={"content-length": str(20 * 1024 * 1024)},
        content=b"{}",
    )
    assert response.status_code == 413


def test_untrusted_host_is_rejected():
    response = TestClient(app).get("/health", headers={"host": "attacker.example"})
    assert response.status_code == 400


def test_private_replay_websocket_requires_authentication():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/stream/csv/PRIVATE"):
            pass
    assert exc_info.value.code == 1008


def test_bad_websocket_message_does_not_expose_validation_details():
    client = TestClient(app)
    with client.websocket_connect("/ws/live") as websocket:
        websocket.send_text("not-json")
        assert websocket.receive_json() == {
            "type": "error",
            "code": "bad_message",
            "message": "Invalid message",
        }
