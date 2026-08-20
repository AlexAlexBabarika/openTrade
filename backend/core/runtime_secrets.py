"""Load operator-provided secrets or persist secure local defaults."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

_SECRET_NAMES = ("JWT_SECRET", "API_KEYS_ENCRYPTION_KEY")
_DEFAULT_PATH = ".openquant/secrets.json"
_cached: dict[str, str] | None = None


def _generate() -> dict[str, str]:
    return {name: secrets.token_hex(32) for name in _SECRET_NAMES}


def _load_file(path: Path) -> dict[str, str]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _generate()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.write("\n")
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid secrets file: {path}")
    return data


def load_runtime_secrets() -> dict[str, str]:
    """Return configured secrets, generating missing values in persistent storage."""
    global _cached
    if _cached is not None:
        return _cached

    configured = {name: os.environ.get(name, "").strip() for name in _SECRET_NAMES}
    if all(configured.values()):
        _cached = configured
        path = None
    else:
        path = Path(os.environ.get("OPENQUANT_SECRETS_FILE", _DEFAULT_PATH))
        stored = _load_file(path)
        _cached = {
            name: configured[name] or str(stored.get(name, "")).strip()
            for name in _SECRET_NAMES
        }
    if not all(_cached.values()):
        raise RuntimeError(f"Secrets file is missing required values: {path}")
    if len(_cached["JWT_SECRET"]) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")
    try:
        encryption_key = bytes.fromhex(_cached["API_KEYS_ENCRYPTION_KEY"])
    except ValueError as exc:
        raise RuntimeError(
            "API_KEYS_ENCRYPTION_KEY must be exactly 64 hexadecimal characters"
        ) from exc
    if len(encryption_key) != 32:
        raise RuntimeError(
            "API_KEYS_ENCRYPTION_KEY must be exactly 64 hexadecimal characters"
        )
    return _cached


def runtime_secret(name: str) -> str:
    if name not in _SECRET_NAMES:
        raise KeyError(name)
    return load_runtime_secrets()[name]
