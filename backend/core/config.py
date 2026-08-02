"""Validated security and resource-limit settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class SecuritySettings:
    cors_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    cookie_secure: bool
    cookie_samesite: str
    max_upload_bytes: int
    max_request_bytes: int
    ws_max_connections_per_ip: int
    ws_max_message_bytes: int
    ws_max_messages_per_minute: int
    ws_max_subscriptions: int
    max_concurrent_sweeps: int


@lru_cache
def security_settings() -> SecuritySettings:
    origins = tuple(
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    if "*" in origins:
        raise RuntimeError(
            "CORS_ORIGINS must list explicit origins; '*' is not allowed"
        )
    allowed_hosts = tuple(
        host.strip()
        for host in os.environ.get(
            "ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
        ).split(",")
        if host.strip()
    )
    if not allowed_hosts or "*" in allowed_hosts:
        raise RuntimeError(
            "ALLOWED_HOSTS must list explicit hostnames; '*' is not allowed"
        )

    cookie_secure = os.environ.get("COOKIE_SECURE", "0").strip() == "1"
    cookie_samesite = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()
    if cookie_samesite not in {"lax", "strict", "none"}:
        raise RuntimeError("COOKIE_SAMESITE must be lax, strict, or none")
    if cookie_samesite == "none" and not cookie_secure:
        raise RuntimeError("COOKIE_SAMESITE=none requires COOKIE_SECURE=1")

    max_upload_bytes = _positive_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
    max_request_bytes = _positive_int("MAX_REQUEST_BYTES", 12 * 1024 * 1024)
    if max_request_bytes < max_upload_bytes:
        raise RuntimeError("MAX_REQUEST_BYTES must be at least MAX_UPLOAD_BYTES")

    return SecuritySettings(
        cors_origins=origins,
        allowed_hosts=allowed_hosts,
        cookie_secure=cookie_secure,
        cookie_samesite=cookie_samesite,
        max_upload_bytes=max_upload_bytes,
        max_request_bytes=max_request_bytes,
        ws_max_connections_per_ip=_positive_int("WS_MAX_CONNECTIONS_PER_IP", 20),
        ws_max_message_bytes=_positive_int("WS_MAX_MESSAGE_BYTES", 64 * 1024),
        ws_max_messages_per_minute=_positive_int("WS_MAX_MESSAGES_PER_MINUTE", 120),
        ws_max_subscriptions=_positive_int("WS_MAX_SUBSCRIPTIONS", 20),
        max_concurrent_sweeps=_positive_int("MAX_CONCURRENT_SWEEPS", 2),
    )


def validate_runtime_config() -> None:
    security_settings()
