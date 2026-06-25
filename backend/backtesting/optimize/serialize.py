# backend/backtesting/optimize/serialize.py
"""Canonical JSON serialization of sweeps and walk-forward reports.

Single source of truth for the wire shape the ``/sweeps`` API returns and the
frontend reads. Field names match the TS mirror in
``frontend/src/lib/features/sweep/types.ts``.
"""

from __future__ import annotations

import dataclasses

from backend.backtesting.optimize.types import (
    SweepResult,
    Trial,
    WalkForwardReport,
    WindowResult,
)


def _trial_dict(t: Trial) -> dict:
    return {
        "trial_id": t.trial_id,
        "params": t.params,
        "metrics": t.metrics,
        "equity_hash": t.equity_hash,
        "cached": t.cached,
    }


def sweep_to_dict(res: SweepResult) -> dict:
    return {
        "sweep_id": res.sweep_id,
        "config": dataclasses.asdict(res.config),
        "trials": [_trial_dict(t) for t in res.trials],
        "best_trial_id": res.best_trial_id,
    }


def _window_result_dict(w: WindowResult) -> dict:
    return {
        "window": dataclasses.asdict(w.window),
        "best_params": w.best_params,
        "is_metric": w.is_metric,
        "oos_metrics": w.oos_metrics,
    }


def walk_forward_to_dict(report: WalkForwardReport) -> dict:
    return {
        "metric": report.metric,
        "windows": [_window_result_dict(w) for w in report.windows],
        "oos_metrics": report.oos_metrics,
        "is_aggregate": report.is_aggregate,
        "oos_aggregate": report.oos_aggregate,
    }
