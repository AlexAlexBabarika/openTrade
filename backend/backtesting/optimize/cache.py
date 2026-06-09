# backend/backtesting/optimize/cache.py
"""Result deduplication for sweeps.

A trial is uniquely identified by ``(strategy code, params, data version, seed)``.
Because the engine is deterministic, identical keys map to identical results — so
random search hitting the same combo twice, or a re-run of a grid, costs nothing.
The cache is in-memory and scoped to one sweep (enough for the determinism +
caching acceptance criteria); a disk-backed variant can replace it later.
"""

from __future__ import annotations

import hashlib
import json


def trial_key(
    *, code_hash: str, params: dict, data_version: str | None, seed: int
) -> str:
    payload = json.dumps(
        {"code": code_hash, "params": params, "data": data_version, "seed": seed},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class TrialCache:
    """In-memory key -> trial-payload map."""

    def __init__(self) -> None:
        self._d: dict[str, dict] = {}

    def get(self, key: str) -> dict | None:
        return self._d.get(key)

    def put(self, key: str, value: dict) -> None:
        self._d[key] = value
