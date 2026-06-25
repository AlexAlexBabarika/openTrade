"""
Sizers turn signals into target weights and nothing else — they are pure
functions of their inputs (no ctx, no I/O, sorted-symbol determinism), so the
same signals always produce the same allocation and sizing can be swapped
without touching strategy logic. A custom sizer is just any user function
returning a weights dict.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from backend.backtesting.costs import Costs
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.sizers import (
    equal_weight,
    inverse_volatility,
    kelly_weight,
    kelly_weights,
    trailing_volatility,
)
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import Bar


def test_equal_weight_splits_gross_across_symbols() -> None:
    assert equal_weight(["AAPL", "MSFT", "GOOG", "AMZN"]) == {
        "AAPL": 0.25,
        "AMZN": 0.25,
        "GOOG": 0.25,
        "MSFT": 0.25,
    }


def test_equal_weight_respects_signal_signs_and_drops_zeros() -> None:
    weights = equal_weight({"AAPL": 1.0, "MSFT": -2.0, "GOOG": 0.0})
    assert weights == {"AAPL": 0.5, "MSFT": -0.5}


def test_equal_weight_gross_scaling_and_empty() -> None:
    assert equal_weight(["AAPL", "MSFT"], gross=0.5) == {"AAPL": 0.25, "MSFT": 0.25}
    assert equal_weight([]) == {}
    assert equal_weight({"AAPL": 0.0}) == {}


def test_inverse_volatility_weights_low_vol_names_heavier() -> None:
    weights = inverse_volatility({"AAPL": 0.1, "MSFT": 0.2})
    assert weights["AAPL"] == pytest.approx(2.0 / 3.0)
    assert weights["MSFT"] == pytest.approx(1.0 / 3.0)


def test_inverse_volatility_signs_gross_and_bad_vols() -> None:
    weights = inverse_volatility(
        {"AAPL": 0.1, "MSFT": 0.1, "GOOG": 0.0},
        signals={"AAPL": 1.0, "MSFT": -1.0, "GOOG": 1.0},
        gross=2.0,
    )
    # GOOG excluded (non-positive vol); remaining split gross 2.0 equally.
    assert weights == {"AAPL": 1.0, "MSFT": -1.0}
    assert inverse_volatility({}) == {}


def test_inverse_volatility_drops_symbols_with_zero_signal() -> None:
    weights = inverse_volatility(
        {"AAPL": 0.1, "MSFT": 0.1}, signals={"AAPL": 1.0, "MSFT": 0.0}
    )
    assert weights == {"AAPL": 1.0}


def test_kelly_weight_is_fractional_edge_over_variance() -> None:
    assert kelly_weight(edge=0.05, variance=0.04) == pytest.approx(1.25)
    assert kelly_weight(edge=0.05, variance=0.04, fraction=0.5) == pytest.approx(0.625)
    assert kelly_weight(edge=-0.02, variance=0.04) == pytest.approx(-0.5)
    assert kelly_weight(edge=0.05, variance=0.0) == 0.0  # undefined -> flat


def test_kelly_weights_maps_per_symbol() -> None:
    weights = kelly_weights(
        edges={"AAPL": 0.05, "MSFT": -0.02},
        variances={"AAPL": 0.04, "MSFT": 0.04},
        fraction=0.5,
    )
    assert weights == {
        "AAPL": pytest.approx(0.625),
        "MSFT": pytest.approx(-0.25),
    }
    # A symbol without a variance is dropped rather than guessed at.
    assert kelly_weights(edges={"AAPL": 0.05}, variances={}) == {}


def _bars(closes: list[float]) -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(
            time=start + timedelta(days=i),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=0.0,
        )
        for i, c in enumerate(closes)
    ]


def test_trailing_volatility_matches_sample_std_of_returns() -> None:
    # Returns: +10%, -10% -> sample std of [0.1, -0.1]
    vol = trailing_volatility(_bars([100.0, 110.0, 99.0]), lookback=2)
    import statistics

    assert vol == pytest.approx(statistics.stdev([0.1, -0.1]))


def test_trailing_volatility_uses_only_the_lookback_window() -> None:
    # The wild early move must be outside a lookback of 2.
    flat_recent = _bars([1.0, 1000.0, 1000.0, 1000.0])
    assert trailing_volatility(flat_recent, lookback=2) == pytest.approx(0.0)


def test_trailing_volatility_needs_at_least_two_returns() -> None:
    assert trailing_volatility(_bars([100.0, 110.0]), lookback=5) is None
    assert trailing_volatility(_bars([]), lookback=5) is None


def test_equal_weight_drives_rebalance_to_one_over_n() -> None:
    frames = {
        "AAPL": pl.DataFrame(
            {
                "timestamp": [
                    datetime(2024, 1, d, tzinfo=timezone.utc) for d in (1, 2, 3)
                ],
                "open": [10.0] * 3,
                "high": [11.0] * 3,
                "low": [9.0] * 3,
                "close": [10.0] * 3,
                "volume": [1000.0] * 3,
            }
        ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC")),
        "MSFT": pl.DataFrame(
            {
                "timestamp": [
                    datetime(2024, 1, d, tzinfo=timezone.utc) for d in (1, 2, 3)
                ],
                "open": [20.0] * 3,
                "high": [21.0] * 3,
                "low": [19.0] * 3,
                "close": [20.0] * 3,
                "volume": [1000.0] * 3,
            }
        ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC")),
    }

    class OneOverN(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                for symbol, weight in equal_weight(ctx.universe).items():
                    ctx.target_weight(symbol, weight)
                ctx.rebalance()

    result = run_portfolio_backtest(
        frames=frames,
        strategy=OneOverN(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    assert result.equity_curve[-1].weights == {"AAPL": 0.5, "MSFT": 0.5}
