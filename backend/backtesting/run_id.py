"""Content-addressed run identity.

``run_key`` is the run's address: identical inputs hash to the same id, so a
re-run of an identical configuration is a no-op write (dedup). It mirrors the
sweep cache's ``trial_key`` shape, extended with engine version and the full
config dict.
"""

from __future__ import annotations

import hashlib
import json

from backend.backtesting.version import ENGINE_VERSION


def run_key(
    *,
    engine_version: str,
    ast_hash: str,
    params: dict,
    data_version: str | None,
    seed: int,
    config: dict,
) -> str:
    payload = json.dumps(
        {
            "engine_version": engine_version,
            "ast_hash": ast_hash,
            "params": params,
            "data_version": data_version,
            "seed": seed,
            "config": config,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def run_status(meta: dict) -> dict:
    recorded = meta.get("engine_version", "unknown")
    return {
        "stale": recorded != ENGINE_VERSION,
        "recorded": recorded,
        "current": ENGINE_VERSION,
    }
