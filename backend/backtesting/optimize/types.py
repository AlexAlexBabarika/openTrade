# backend/backtesting/optimize/types.py
"""Value types produced by sweeps and walk-forward, plus objective extraction."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Trial:
    """One evaluated parameter combination.

    ``metrics`` is the serialized ``Metrics`` dict; ``equity_hash`` is the stable
    equity-curve hash used to prove determinism; ``cached`` is True when the
    result was served from the trial cache rather than recomputed.
    """

    trial_id: int
    params: dict
    metrics: dict
    equity_hash: str
    cached: bool = False


@dataclass(frozen=True, slots=True)
class SweepConfig:
    """Inputs that fully determine a sweep (and therefore its results)."""

    search: str  # "grid" | "random"
    metric: str  # objective field name on Metrics, e.g. "sharpe"
    vary: list[str]
    n_random: int = 200
    seed: int = 0
    starting_cash: float = 100_000.0
    data_version: str | None = None
    fixed: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SweepResult:
    sweep_id: str
    config: SweepConfig
    trials: list[Trial]
    best_trial_id: int | None


@dataclass(frozen=True, slots=True)
class Window:
    index: int
    is_start: int  # bar index, inclusive
    is_end: int  # exclusive
    oos_start: int
    oos_end: int  # exclusive


@dataclass(frozen=True, slots=True)
class WindowResult:
    window: Window
    best_params: dict
    is_metric: float
    oos_metrics: dict


@dataclass(frozen=True, slots=True)
class WalkForwardReport:
    metric: str
    windows: list[WindowResult]
    oos_metrics: dict  # metrics on the concatenated OOS equity
    is_aggregate: float  # mean IS objective across windows
    oos_aggregate: float  # mean OOS objective across windows


def metric_value(metrics: dict, name: str) -> float:
    """The objective value for maximization; missing/None -> -inf (worst)."""
    v = metrics.get(name)
    return float(v) if v is not None else -math.inf
