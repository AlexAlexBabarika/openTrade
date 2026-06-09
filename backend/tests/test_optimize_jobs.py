# backend/tests/test_optimize_jobs.py
"""The in-process sweep registry: start, poll to completion, cancel."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl

from backend.backtesting.optimize.jobs import SweepRegistry
from backend.backtesting.optimize.types import SweepConfig

CODE = (
    "params = {'qty': Int(1, 4, step=1)}\n"
    "def on_bar(ctx):\n"
    "    if ctx.position.quantity == 0:\n"
    "        ctx.buy(ctx.params['qty'])\n"
)


def _frame(n: int = 80) -> pl.DataFrame:
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
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


def _await(reg: SweepRegistry, sid: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = reg.get(sid)
        if job and job.status in {"done", "error", "cancelled"}:
            return
        time.sleep(0.05)
    raise AssertionError("sweep did not finish in time")


def test_start_then_poll_to_done() -> None:
    reg = SweepRegistry()
    cfg = SweepConfig(search="grid", metric="total_return", vary=["qty"])
    sid = reg.start(code=CODE, frame=_frame(), config=cfg)
    _await(reg, sid)
    job = reg.get(sid)
    assert job.status == "done"
    assert job.total == 4
    assert job.done == 4
    assert job.result is not None
    assert job.result["best_trial_id"] is not None


def test_unknown_id_returns_none() -> None:
    assert SweepRegistry().get("nope") is None
