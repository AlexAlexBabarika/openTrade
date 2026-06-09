# backend/backtesting/optimize/jobs.py
"""In-process registry of running sweeps.

A sweep runs on a daemon thread; the HTTP layer starts it and then polls a
snapshot of progress (done/total, partial trials, best-so-far, and the full
serialized result once finished). State is mutated under a lock. This is the
single-process counterpart to a job queue — sufficient for the laptop-scale
acceptance target; a durable queue can replace ``SweepRegistry`` without touching
the runner or the routes.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

import polars as pl

from backend.backtesting.optimize.runner import run_sweep
from backend.backtesting.optimize.serialize import sweep_to_dict
from backend.backtesting.optimize.types import SweepConfig, Trial


@dataclass
class SweepJob:
    sweep_id: str
    status: str = "running"  # running | done | error | cancelled
    total: int = 0
    done: int = 0
    trials: list[dict] = field(default_factory=list)
    best_trial_id: int | None = None
    best_metric: float | None = None
    error: str | None = None
    result: dict | None = None
    _cancel: threading.Event = field(default_factory=threading.Event)


class SweepRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, SweepJob] = {}
        self._lock = threading.Lock()

    def start(self, *, code: str, frame: pl.DataFrame, config: SweepConfig) -> str:
        sweep_id = uuid.uuid4().hex
        job = SweepJob(sweep_id=sweep_id)
        with self._lock:
            self._jobs[sweep_id] = job
        t = threading.Thread(
            target=self._run, args=(job, code, frame, config), daemon=True
        )
        t.start()
        return sweep_id

    def get(self, sweep_id: str) -> SweepJob | None:
        with self._lock:
            return self._jobs.get(sweep_id)

    def cancel(self, sweep_id: str) -> bool:
        job = self.get(sweep_id)
        if job is None:
            return False
        job._cancel.set()
        return True

    def _run(
        self, job: SweepJob, code: str, frame: pl.DataFrame, config: SweepConfig
    ) -> None:
        metric = config.metric

        def progress(done: int, total: int, trial: Trial) -> None:
            with self._lock:
                job.done = done
                job.total = total
                job.trials.append(
                    {
                        "trial_id": trial.trial_id,
                        "params": trial.params,
                        "metrics": trial.metrics,
                        "cached": trial.cached,
                    }
                )
                value = trial.metrics.get(metric)
                if value is not None and (
                    job.best_metric is None or value > job.best_metric
                ):
                    job.best_metric = value
                    job.best_trial_id = trial.trial_id

        try:
            res = run_sweep(
                code=code,
                frame=frame,
                config=config,
                progress=progress,
                should_cancel=job._cancel.is_set,
            )
        except Exception as e:  # surface a clean message to the poller
            with self._lock:
                job.status = "error"
                job.error = str(e)
            return

        with self._lock:
            if job._cancel.is_set():
                job.status = "cancelled"
            else:
                job.status = "done"
                job.best_trial_id = res.best_trial_id
                job.result = sweep_to_dict(res)
