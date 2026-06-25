# backend/tests/test_optimize_cache.py
"""Trial keys hash (code, params, data_version, seed); the cache dedups."""

from __future__ import annotations

from backend.backtesting.optimize.cache import TrialCache, trial_key


def test_key_is_stable_regardless_of_param_dict_order() -> None:
    k1 = trial_key(code_hash="abc", params={"a": 1, "b": 2}, data_version="v1", seed=0)
    k2 = trial_key(code_hash="abc", params={"b": 2, "a": 1}, data_version="v1", seed=0)
    assert k1 == k2


def test_key_changes_with_any_input() -> None:
    base = dict(code_hash="abc", params={"a": 1}, data_version="v1", seed=0)
    k = trial_key(**base)
    assert k != trial_key(**{**base, "code_hash": "def"})
    assert k != trial_key(**{**base, "params": {"a": 2}})
    assert k != trial_key(**{**base, "data_version": "v2"})
    assert k != trial_key(**{**base, "seed": 1})


def test_cache_round_trips() -> None:
    cache = TrialCache()
    assert cache.get("k") is None
    cache.put("k", {"sharpe": 1.5})
    assert cache.get("k") == {"sharpe": 1.5}
