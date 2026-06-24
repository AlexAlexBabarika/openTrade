"""Content-addressed, on-disk run snapshot store.

Layout per run_id, under ``<OPENTRADE_DATA_ROOT or backend/datastore/_data>/runs/``:
    runs/<run_id>/
      meta.json strategy.py params.json config.json metrics.json log.jsonl
      bars.parquet result.json
Writes are atomic (temp dir -> rename) and idempotent (existing id is a no-op).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import polars as pl

from backend.backtesting.run_snapshot import AssembledSnapshot

_DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "datastore" / "_data"


def _bars_frame(bars: dict) -> pl.DataFrame:
    """Single -> a frame; portfolio -> a frame with a ``symbol`` column."""
    if bars["kind"] == "single":
        rows = bars["data"]
        return (
            pl.DataFrame(rows)
            if rows
            else pl.DataFrame(
                schema={
                    "t": pl.Int64,
                    "open": pl.Float64,
                    "high": pl.Float64,
                    "low": pl.Float64,
                    "close": pl.Float64,
                    "volume": pl.Float64,
                }
            )
        )
    rows = [
        {**b, "symbol": sym} for sym, series in bars["data"].items() for b in series
    ]
    return pl.DataFrame(rows)


class RunStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @classmethod
    def default(cls) -> "RunStore":
        env = os.environ.get("OPENTRADE_DATA_ROOT")
        base = Path(env) if env else _DEFAULT_DATA_ROOT
        return cls(base / "runs")

    @property
    def root(self) -> Path:
        return self._root

    def path(self, run_id: str) -> Path:
        return self._root / run_id

    def exists(self, run_id: str) -> bool:
        return (self.path(run_id) / "meta.json").exists()

    def list_ids(self) -> list[str]:
        if not self._root.exists():
            return []
        return sorted(
            p.name for p in self._root.iterdir() if (p / "meta.json").exists()
        )

    def write(self, snap: AssembledSnapshot) -> str:
        if self.exists(snap.run_id):
            return snap.run_id
        self._root.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix=f".{snap.run_id}.", dir=self._root))
        try:
            (tmp / "meta.json").write_text(json.dumps(snap.meta))
            (tmp / "strategy.py").write_text(snap.strategy_code)
            (tmp / "params.json").write_text(json.dumps(snap.params))
            (tmp / "config.json").write_text(json.dumps(snap.config))
            (tmp / "metrics.json").write_text(json.dumps(snap.metrics))
            (tmp / "log.jsonl").write_text(
                "".join(json.dumps(line) + "\n" for line in snap.log)
            )
            (tmp / "result.json").write_text(json.dumps(snap.result_body))
            _bars_frame(snap.bars).write_parquet(tmp / "bars.parquet")
            os.replace(tmp, self.path(snap.run_id))
        finally:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
        return snap.run_id

    def read(self, run_id: str) -> dict:
        d = self.path(run_id)
        if not (d / "meta.json").exists():
            raise FileNotFoundError(f"run {run_id} not found")
        meta = json.loads((d / "meta.json").read_text())
        result_body = json.loads((d / "result.json").read_text())
        bars_df = pl.read_parquet(d / "bars.parquet")
        if "symbol" in bars_df.columns:
            bars: object = {
                sym: sub.drop("symbol").to_dicts()
                for (sym,), sub in bars_df.group_by("symbol", maintain_order=True)
            }
        else:
            bars = bars_df.to_dicts()
        log = [
            json.loads(line)
            for line in (d / "log.jsonl").read_text().splitlines()
            if line.strip()
        ]
        return {
            "meta": meta,
            "params": json.loads((d / "params.json").read_text()),
            "config": json.loads((d / "config.json").read_text()),
            "metrics": json.loads((d / "metrics.json").read_text()),
            "bars": bars,
            "log": log,
            **result_body,
        }
