"""
portfolio_result_to_dict is the canonical wire shape of a portfolio run: one
fully JSON-serializable blob with per-symbol bars, weighted equity points,
symbol-stamped orders/fills/trades, the constraint binding log, and the
portfolio metrics block. The dashboard reads only this.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import polars as pl

from backend.backtesting.costs import Costs
from backend.backtesting.multi.constraints import Constraints
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.serialize import portfolio_result_to_dict
from backend.backtesting.strategy import Strategy

_T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _frame(closes: list[float]) -> pl.DataFrame:
    ts = [_T0 + timedelta(days=i) for i in range(len(closes))]
    return pl.DataFrame(
        {
            "timestamp": ts,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000.0] * len(closes),
        }
    ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))


class Greedy(Strategy):
    def on_bar(self, ctx) -> None:
        if ctx.time.day == 1:
            ctx.target_weight("AAPL", 0.9)  # will be capped
            ctx.target_weight("MSFT", 0.2)
            ctx.rebalance()


def _result():
    return run_portfolio_backtest(
        frames={
            "AAPL": _frame([10.0, 10.5, 10.2, 10.8]),
            "MSFT": _frame([20.0, 19.5, 20.5, 21.0]),
        },
        strategy=Greedy(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
        constraints=Constraints(
            max_position_weight=0.5, sectors={"AAPL": "tech", "MSFT": "tech"}
        ),
        strategy_id="greedy",
    )


def test_blob_shape_and_json_serializability() -> None:
    blob = portfolio_result_to_dict(_result())
    json.dumps(blob)  # fully serializable, no datetimes/dataclasses left

    assert set(blob) == {
        "meta",
        "symbols",
        "bars",
        "orders",
        "fills",
        "equity",
        "trades",
        "constraint_events",
        "metrics",
    }
    assert blob["symbols"] == ["AAPL", "MSFT"]
    assert blob["meta"]["strategy_id"] == "greedy"
    assert len(blob["bars"]["AAPL"]) == 4
    assert len(blob["equity"]) == 4


def test_equity_points_carry_weights_and_fills_carry_symbols() -> None:
    blob = portfolio_result_to_dict(_result())
    final = blob["equity"][-1]
    assert set(final) == {"t", "value", "cash", "holdings", "weights"}
    assert set(final["weights"]) == {"AAPL", "MSFT"}
    assert {f["symbol"] for f in blob["fills"]} == {"AAPL", "MSFT"}
    assert all(o["symbol"] in ("AAPL", "MSFT") for o in blob["orders"])


def test_constraint_log_and_metrics_blocks_serialize() -> None:
    blob = portfolio_result_to_dict(_result())
    events = blob["constraint_events"]
    assert len(events) == 1
    assert events[0]["constraint"] == "max_position_weight"
    assert events[0]["symbol"] == "AAPL"
    assert "capped" in events[0]["detail"]

    metrics = blob["metrics"]
    assert "sharpe" in metrics["portfolio"]
    assert set(metrics["symbol_sharpes"]) == {"AAPL", "MSFT"}
    assert metrics["correlation_symbols"] == ["AAPL", "MSFT"]
    assert isinstance(metrics["turnover_per_event"], list)
    assert metrics["turnover_per_event"][0]["index"] == 1
    assert len(metrics["sector_exposure"]) == 4  # sectors map was provided
