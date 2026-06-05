"""Canonical serialization of a ``BacktestResult``.

``result_to_dict`` is the single source of truth for the on-the-wire shape: a
fully JSON-serializable dict with bars inline. ``write_result`` persists it to a
directory as ``run.json`` plus a ``bars.parquet`` sidecar (bars are columnar and
the largest part of the blob); ``read_result`` reattaches the bars. The dashboard
is a pure reader of this output.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import polars as pl

from backend.backtesting.types import (
    BacktestResult,
    Bar,
    EquityPoint,
    Fill,
    Order,
    Trade,
)

_BARS_FILE = "bars.parquet"
_RUN_FILE = "run.json"


def _bar_dict(b: Bar) -> dict:
    return {
        "t": int(b.time.timestamp()),
        "open": b.open,
        "high": b.high,
        "low": b.low,
        "close": b.close,
        "volume": b.volume,
    }


def _order_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "side": o.side.value,
        "quantity": o.quantity,
        "type": o.type.value,
        "limit": o.limit,
        "stop": o.stop,
        "submitted_index": o.submitted_index,
        "triggered": o.triggered,
    }


def _fill_dict(f: Fill) -> dict:
    return {
        "order_id": f.order_id,
        "side": f.side.value,
        "quantity": f.quantity,
        "price": f.price,
        "reference_price": f.reference_price,
        "slippage": f.slippage,
        "spread_cost": f.spread_cost,
        "commission": f.commission,
        "submitted_index": f.submitted_index,
        "fill_index": f.fill_index,
        "reason": f.reason,
    }


def _equity_dict(p: EquityPoint) -> dict:
    return {
        "t": int(p.time.timestamp()),
        "value": p.equity,
        "cash": p.cash,
        "holdings": p.holdings,
    }


def _trade_dict(t: Trade) -> dict:
    return {
        "direction": t.direction.value,
        "quantity": t.quantity,
        "entry_time": t.entry_time.isoformat(),
        "exit_time": t.exit_time.isoformat(),
        "entry_index": t.entry_index,
        "exit_index": t.exit_index,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "pnl": t.pnl,
        "pnl_pct": t.pnl_pct,
        "bars_held": t.bars_held,
    }


def result_to_dict(result: BacktestResult) -> dict:
    """The canonical, fully JSON-serializable blob (bars inline)."""
    meta = dataclasses.asdict(result.meta)
    meta["started_at"] = result.meta.started_at.isoformat()
    meta["finished_at"] = result.meta.finished_at.isoformat()
    return {
        "meta": meta,
        "bars": [_bar_dict(b) for b in result.bars],
        "orders": [_order_dict(o) for o in result.orders],
        "fills": [_fill_dict(f) for f in result.fills],
        "equity": [_equity_dict(p) for p in result.equity_curve],
        "trades": [_trade_dict(t) for t in result.trades],
        "metrics": dataclasses.asdict(result.metrics),
    }


def write_result(result: BacktestResult, directory: Path) -> Path:
    """Persist to ``directory`` as ``run.json`` + ``bars.parquet``; return the dir."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    blob = result_to_dict(result)
    bars = blob.pop("bars")
    pl.DataFrame(bars).write_parquet(directory / _BARS_FILE)
    blob["bars"] = _BARS_FILE
    (directory / _RUN_FILE).write_text(json.dumps(blob))
    return directory


def read_result(directory: Path) -> dict:
    """Load ``run.json`` and reattach bars from the Parquet sidecar."""
    directory = Path(directory)
    blob = json.loads((directory / _RUN_FILE).read_text())
    if blob.get("bars") == _BARS_FILE:
        blob["bars"] = pl.read_parquet(directory / _BARS_FILE).to_dicts()
    return blob
