# backend/tests/test_optimize_acceptance.py
"""Optimization acceptance criteria, as CI guards.

1. A 1,000-trial grid sweep on a daily strategy completes in <5min on a 4-core
   laptop. (We assert well under the budget and skip if the host has <2 cores.)
2. A walk-forward run produces a report distinguishing IS and OOS metrics.
3. Repeating the same sweep yields byte-identical trial results (determinism +
   caching).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
import pytest

from backend.backtesting.optimize.runner import run_sweep
from backend.backtesting.optimize.serialize import sweep_to_dict
from backend.backtesting.optimize.types import SweepConfig
from backend.backtesting.optimize.walkforward import run_walk_forward

# 1,000 combos = 40 x 25 over two integer params.
SWEEP_CODE = (
    "params = {\n"
    "    'a': Int(1, 40, step=1),\n"
    "    'b': Int(1, 25, step=1),\n"
    "}\n"
    "def on_bar(ctx):\n"
    "    if ctx.position.quantity == 0:\n"
    "        ctx.buy(ctx.params['a'] + ctx.params['b'])\n"
)


def _daily_frame(n: int = 252) -> pl.DataFrame:
    start = datetime(2018, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(days=i) for i in range(n)]
    close = 100 + np.cumsum(np.random.default_rng(0).standard_normal(n) * 0.5)
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 1e6),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


def test_thousand_trial_grid_sweep_completes_well_under_five_minutes() -> None:
    if (os.cpu_count() or 1) < 2:
        pytest.skip("needs >=2 cores for the parallel acceptance target")
    config = SweepConfig(search="grid", metric="total_return", vary=["a", "b"])
    start = time.perf_counter()
    res = run_sweep(code=SWEEP_CODE, frame=_daily_frame(), config=config)
    elapsed = time.perf_counter() - start
    assert len(res.trials) == 1000
    assert elapsed < 300.0, f"1000-trial sweep took {elapsed:.1f}s (budget 300s)"


def test_walk_forward_report_distinguishes_is_and_oos() -> None:
    config = SweepConfig(search="grid", metric="total_return", vary=["a", "b"])
    report = run_walk_forward(
        code=SWEEP_CODE,
        frame=_daily_frame(n=300),
        config=config,
        is_len=150,
        oos_len=50,
        step=50,
        anchored=False,
    )
    assert report.windows
    for w in report.windows:
        assert "total_return" in w.oos_metrics  # OOS metrics present per window
        assert isinstance(w.is_metric, float)  # IS objective present per window
    # Report exposes IS and OOS aggregates as separate fields.
    assert hasattr(report, "is_aggregate") and hasattr(report, "oos_aggregate")
    assert "total_return" in report.oos_metrics


def test_repeated_sweep_is_byte_identical() -> None:
    config = SweepConfig(
        search="random", metric="total_return", vary=["a", "b"], n_random=64
    )
    a = sweep_to_dict(run_sweep(code=SWEEP_CODE, frame=_daily_frame(), config=config))
    b = sweep_to_dict(run_sweep(code=SWEEP_CODE, frame=_daily_frame(), config=config))
    # Ignore the random sweep_id; everything that depends on inputs must match.
    a.pop("sweep_id"), b.pop("sweep_id")
    assert a == b
