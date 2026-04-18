"""
Populate ``public.symbols`` from each provider's native catalog.

Usage:
    python -m backend.scripts.seed_symbols
    python -m backend.scripts.seed_symbols --providers twelvedata,binance

Requires ``SUPABASE_URL`` + ``SUPABASE_SERVICE_ROLE_KEY`` in the environment.
Twelve Data additionally requires ``TWELVEDATA_API_KEY``.

Idempotent: upserts by ``symbol``, setting the per-provider boolean to ``true``
without touching other providers' flags. No deletions — a symbol that drops off
a provider's list keeps its previous flag until manually pruned.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Callable


def _load_dotenv() -> None:
    """Populate os.environ from ``.env`` at the repo root if present.

    Minimal parser: ``KEY=VALUE`` per line, ``#`` comments, optional surrounding
    quotes. Does not override values already set in the environment.
    """
    root = Path(__file__).resolve().parents[2]
    env_file = root / ".env"
    if not env_file.is_file():
        return
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

from backend.core.supabase_client import (  # noqa: E402
    get_service_postgrest,
    is_supabase_configured,
)
from backend.market.data_sources.binance_loader import BinanceProvider  # noqa: E402
from backend.market.data_sources.twelvedataprovider import (
    TwelveDataProvider,
)  # noqa: E402
from backend.models.market_data_models import SymbolRecord  # noqa: E402

logger = logging.getLogger("seed_symbols")

# Upsert in chunks — PostgREST tolerates large payloads, but smaller batches
# give clearer per-batch progress on ~100k-row Twelve Data dumps.
_BATCH_SIZE = 2000

ProviderLoader = Callable[[], list[SymbolRecord]]


def _load_twelvedata() -> list[SymbolRecord]:
    api_key = os.environ.get("TWELVEDATA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "TWELVEDATA_API_KEY is not set. Export it or drop 'twelvedata' from --providers."
        )
    return TwelveDataProvider(api_key=api_key).list_symbols()


def _load_binance() -> list[SymbolRecord]:
    # BinanceProvider() with no user_id uses a public Client — exchange_info is public.
    return BinanceProvider().list_symbols()


_LOADERS: dict[str, ProviderLoader] = {
    "twelvedata": _load_twelvedata,
    "binance": _load_binance,
}


def _row(record: SymbolRecord, provider: str) -> dict:
    return {
        "symbol": record.symbol.strip().upper(),
        "name": record.name,
        "asset_type": record.asset_type.value if record.asset_type else None,
        "exchange": record.exchange,
        provider: True,
    }


def _upsert_batch(provider: str, rows: list[dict]) -> int:
    db = get_service_postgrest()
    # ``on_conflict=symbol`` + default Prefer: resolution=merge-duplicates means
    # unspecified columns (other provider flags) are preserved on conflict.
    resp = db.from_("symbols").upsert(rows, on_conflict="symbol").execute()
    return len(resp.data) if resp.data else len(rows)


def _seed_provider(provider: str) -> None:
    loader = _LOADERS[provider]
    logger.info("Fetching %s symbol list…", provider)
    records = loader()
    logger.info("%s returned %d symbols", provider, len(records))
    if not records:
        return

    # De-dupe by (upper) symbol within this provider's feed.
    seen: dict[str, SymbolRecord] = {}
    for r in records:
        key = r.symbol.strip().upper()
        if key and key not in seen:
            seen[key] = r
    deduped = list(seen.values())

    total = 0
    for i in range(0, len(deduped), _BATCH_SIZE):
        chunk = deduped[i : i + _BATCH_SIZE]
        rows = [_row(r, provider) for r in chunk]
        written = _upsert_batch(provider, rows)
        total += written
        logger.info(
            "%s: upserted %d/%d (batch %d)",
            provider,
            min(i + _BATCH_SIZE, len(deduped)),
            len(deduped),
            written,
        )
    logger.info("%s: done (%d rows)", provider, total)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Seed public.symbols from providers.")
    parser.add_argument(
        "--providers",
        default=",".join(_LOADERS.keys()),
        help=f"Comma-separated subset of {sorted(_LOADERS.keys())}",
    )
    args = parser.parse_args(argv)

    if not is_supabase_configured():
        logger.error(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
        return 2

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    unknown = [p for p in providers if p not in _LOADERS]
    if unknown:
        logger.error("Unknown provider(s): %s", ", ".join(unknown))
        return 2

    failed: list[str] = []
    for provider in providers:
        try:
            _seed_provider(provider)
        except Exception as e:
            logger.exception("Failed seeding %s: %s", provider, e)
            failed.append(provider)
    if failed:
        logger.error("Seed failed for: %s", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
