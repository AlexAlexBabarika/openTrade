import json

import pytest

from backend.core import runtime_secrets


@pytest.fixture(autouse=True)
def reset_cache(monkeypatch):
    runtime_secrets._cached = None
    for name in runtime_secrets._SECRET_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_generates_and_reuses_persistent_secrets(tmp_path, monkeypatch):
    path = tmp_path / "secrets.json"
    monkeypatch.setenv("OPENQUANT_SECRETS_FILE", str(path))

    first = runtime_secrets.load_runtime_secrets()
    runtime_secrets._cached = None
    second = runtime_secrets.load_runtime_secrets()

    assert first == second
    assert all(len(value) == 64 for value in first.values())
    assert path.stat().st_mode & 0o777 == 0o600


def test_environment_values_take_precedence(tmp_path, monkeypatch):
    path = tmp_path / "secrets.json"
    path.write_text(
        json.dumps({name: "a" * 64 for name in runtime_secrets._SECRET_NAMES})
    )
    monkeypatch.setenv("OPENQUANT_SECRETS_FILE", str(path))
    monkeypatch.setenv("JWT_SECRET", "configured" * 4)

    loaded = runtime_secrets.load_runtime_secrets()

    assert loaded["JWT_SECRET"] == "configured" * 4
    assert loaded["API_KEYS_ENCRYPTION_KEY"] == "a" * 64


def test_does_not_create_file_when_both_values_are_configured(tmp_path, monkeypatch):
    path = tmp_path / "secrets.json"
    monkeypatch.setenv("OPENQUANT_SECRETS_FILE", str(path))
    for name in runtime_secrets._SECRET_NAMES:
        monkeypatch.setenv(name, "a" * 64)

    assert runtime_secrets.load_runtime_secrets()
    assert not path.exists()


def test_rejects_invalid_operator_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENQUANT_SECRETS_FILE", str(tmp_path / "secrets.json"))
    monkeypatch.setenv("JWT_SECRET", "too-short")
    monkeypatch.setenv("API_KEYS_ENCRYPTION_KEY", "not-hex")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        runtime_secrets.load_runtime_secrets()
