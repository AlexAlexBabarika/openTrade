from datetime import datetime, timezone

import polars as pl

from backend.backtesting.multi.sandbox import run_portfolio_strategy
from backend.backtesting.multi.universe import Membership, Universe


def _frame(times, price):
    return pl.DataFrame(
        {
            "timestamp": times,
            "open": [price] * len(times),
            "high": [price] * len(times),
            "low": [price] * len(times),
            "close": [price] * len(times),
            "volume": [100.0] * len(times),
        },
        schema={
            "timestamp": pl.Datetime("us", "UTC"),
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Float64,
        },
    )


CODE = "def on_bar(ctx):\n    pass\n"


def test_data_version_recorded_in_meta():
    times = [datetime(2021, 1, d, tzinfo=timezone.utc) for d in (4, 5)]
    frames = {"AAPL": _frame(times, 10.0)}
    result = run_portfolio_strategy(CODE, frames, data_version="abc123")
    assert result.meta.get("data_version") == "abc123"


def test_universe_restricts_active_symbols():
    times = [datetime(2021, 1, d, tzinfo=timezone.utc) for d in (4, 5)]
    frames = {"AAPL": _frame(times, 10.0), "MSFT": _frame(times, 20.0)}
    # MSFT joins only on day 5; universe is passed explicitly.
    universe = Universe(
        [
            Membership("AAPL"),
            Membership("MSFT", start=datetime(2021, 1, 5, tzinfo=timezone.utc)),
        ]
    )
    result = run_portfolio_strategy(CODE, frames, universe=universe)
    assert result.status == "ok"
    assert set(result.symbols) == {"AAPL", "MSFT"}
