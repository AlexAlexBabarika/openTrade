# backend/backtesting/optimize/search.py
"""Search strategies: how the parameter space is enumerated.

Both are deterministic: ``grid`` iterates keys in sorted order so the trial
ordering is stable across runs; ``random_search`` draws from a single seeded RNG.
Duplicate draws are intentionally allowed — the trial cache dedups them and the
*distribution* of results is the point. Bayesian search is deferred.
"""

from __future__ import annotations

import itertools
import math
import random
from typing import Iterator

from backend.backtesting.optimize.space import Param


def grid_size(space: dict[str, Param]) -> int:
    return math.prod(len(p.values()) for p in space.values()) if space else 0


def grid(space: dict[str, Param]) -> Iterator[dict]:
    keys = sorted(space)
    value_lists = [space[k].values() for k in keys]
    for combo in itertools.product(*value_lists):
        yield dict(zip(keys, combo))


def random_search(space: dict[str, Param], *, n: int, seed: int) -> Iterator[dict]:
    rng = random.Random(seed)
    keys = sorted(space)
    for _ in range(n):
        yield {k: space[k].sample(rng) for k in keys}
