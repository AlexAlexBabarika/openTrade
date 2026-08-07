from backend.scripts import seed_symbols


def test_seed_providers_runs_every_requested_provider(monkeypatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(seed_symbols, "_seed_provider", called.append)

    assert seed_symbols.seed_providers(["binance", "twelvedata"]) == []
    assert called == ["binance", "twelvedata"]


def test_seed_providers_reports_failures_without_skipping_rest(monkeypatch) -> None:
    called: list[str] = []

    def run(provider: str) -> None:
        called.append(provider)
        if provider == "binance":
            raise RuntimeError("offline")

    monkeypatch.setattr(seed_symbols, "_seed_provider", run)

    assert seed_symbols.seed_providers(["binance", "twelvedata"]) == ["binance"]
    assert called == ["binance", "twelvedata"]


def test_seed_providers_rejects_unknown_provider() -> None:
    try:
        seed_symbols.seed_providers(["unknown"])
    except ValueError as exc:
        assert "Unknown provider" in str(exc)
    else:
        raise AssertionError("unknown provider was accepted")
