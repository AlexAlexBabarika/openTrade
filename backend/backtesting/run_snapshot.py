"""Assemble an immutable run snapshot from a canonical result blob + inputs.

Pure: turns the on-the-wire blob (``result_to_dict`` /
``portfolio_result_to_dict``) plus the run inputs into the exact set of files
the store persists, and computes the content-addressed ``run_id``. No I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.backtesting.run_config import RunInputs, config_to_dict
from backend.backtesting.run_id import run_key
from backend.scripts.ast_guard import ast_hash


@dataclass
class AssembledSnapshot:
    run_id: str
    kind: str  # "single" | "portfolio"
    meta: dict
    strategy_code: str
    params: dict
    config: dict
    metrics: dict
    log: list[dict]
    result_body: dict
    bars: dict  # {"kind": "single"|"portfolio", "data": ...}


def _event_times(blob: dict, kind: str) -> list[datetime]:
    if kind == "single":
        return [datetime.fromtimestamp(b["t"], tz=timezone.utc) for b in blob["bars"]]
    times: set[int] = set()
    for series in blob["bars"].values():
        times.update(b["t"] for b in series)
    return [datetime.fromtimestamp(t, tz=timezone.utc) for t in sorted(times)]


def assemble_snapshot(blob: dict, inputs: RunInputs) -> AssembledSnapshot:
    kind = "portfolio" if isinstance(blob.get("bars"), dict) else "single"
    code_h = ast_hash(inputs.code)
    config = config_to_dict(inputs, event_times=_event_times(blob, kind))

    run_id = run_key(
        engine_version=blob["meta"]["engine_version"],
        ast_hash=code_h,
        params=inputs.params,
        data_version=inputs.data_version,
        seed=inputs.seed,
        config=config,
    )

    meta = {
        **blob["meta"],
        "run_id": run_id,
        "ast_hash": code_h,
        "starting_cash": inputs.starting_cash,
        "data_version": inputs.data_version,
        "seed": inputs.seed,
    }

    result_body = {
        "orders": blob["orders"],
        "fills": blob["fills"],
        "equity": blob["equity"],
        "trades": blob["trades"],
    }
    log: list[dict] = []
    if kind == "portfolio":
        result_body["symbols"] = blob["symbols"]
        log = list(blob.get("constraint_events", []))

    return AssembledSnapshot(
        run_id=run_id,
        kind=kind,
        meta=meta,
        strategy_code=inputs.code,
        params=inputs.params,
        config=config,
        metrics=blob["metrics"],
        log=log,
        result_body=result_body,
        bars={"kind": kind, "data": blob["bars"]},
    )
