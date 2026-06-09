# backend/tests/test_optimize_serialize.py
"""The canonical sweep/walk-forward blobs are JSON-serializable and complete."""

from __future__ import annotations

import json

from backend.backtesting.optimize.serialize import sweep_to_dict, walk_forward_to_dict
from backend.backtesting.optimize.types import (
    SweepConfig,
    SweepResult,
    Trial,
    WalkForwardReport,
    Window,
    WindowResult,
)


def _sweep() -> SweepResult:
    cfg = SweepConfig(search="grid", metric="sharpe", vary=["qty"])
    trials = [
        Trial(0, {"qty": 1}, {"sharpe": 0.5}, "h0", cached=False),
        Trial(1, {"qty": 2}, {"sharpe": 1.2}, "h1", cached=True),
    ]
    return SweepResult("sid", cfg, trials, best_trial_id=1)


def test_sweep_to_dict_is_json_serializable_and_keeps_fields() -> None:
    blob = sweep_to_dict(_sweep())
    json.dumps(blob)  # must not raise
    assert blob["sweep_id"] == "sid"
    assert blob["best_trial_id"] == 1
    assert blob["config"]["metric"] == "sharpe"
    assert blob["config"]["vary"] == ["qty"]
    assert blob["trials"][1]["cached"] is True
    assert blob["trials"][0]["metrics"]["sharpe"] == 0.5


def test_walk_forward_to_dict_round_trips() -> None:
    report = WalkForwardReport(
        metric="sharpe",
        windows=[
            WindowResult(Window(0, 0, 100, 100, 130), {"qty": 2}, 1.1, {"sharpe": 0.4})
        ],
        oos_metrics={"sharpe": 0.4},
        is_aggregate=1.1,
        oos_aggregate=0.4,
    )
    blob = walk_forward_to_dict(report)
    json.dumps(blob)
    assert blob["windows"][0]["best_params"] == {"qty": 2}
    assert blob["windows"][0]["window"]["oos_end"] == 130
    assert blob["oos_aggregate"] == 0.4
