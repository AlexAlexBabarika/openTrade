"""
Rebalance policies decide *when* to trade toward targets; ctx.rebalance()
decides *what*. Periodic fires on calendar-period boundaries (detected
causally — the first bar of a new period, never the unknowable last bar of
the old one), threshold fires when actual weights drift beyond a tolerance,
and signal-driven fires when the declared targets change.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from backend.backtesting.costs import Costs
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.policies import (
    PeriodicRebalance,
    SignalRebalance,
    ThresholdRebalance,
)
from backend.backtesting.strategy import Strategy


class _Ctx:
    """Minimal stand-in exposing what policies read."""

    def __init__(
        self,
        time: datetime,
        weights: dict[str, float] | None = None,
        targets: dict[str, float] | None = None,
    ) -> None:
        self.time = time
        self.weights = weights or {}
        self.targets = targets or {}


def _t(month: int, day: int) -> datetime:
    return datetime(2024, month, day, tzinfo=timezone.utc)


def test_periodic_monthly_fires_on_first_bar_of_each_month() -> None:
    policy = PeriodicRebalance("monthly")
    fired = [
        policy.should_rebalance(_Ctx(t))
        for t in (_t(1, 30), _t(1, 31), _t(2, 1), _t(2, 2), _t(3, 1))
    ]
    assert fired == [True, False, True, False, True]


def test_periodic_daily_fires_once_per_day() -> None:
    policy = PeriodicRebalance("daily")
    times = [_t(1, 1), _t(1, 1), _t(1, 2)]
    assert [policy.should_rebalance(_Ctx(t)) for t in times] == [True, False, True]


def test_periodic_weekly_fires_on_iso_week_change() -> None:
    policy = PeriodicRebalance("weekly")
    # 2024-01-05 is Friday, 01-07 Sunday (same ISO week), 01-08 Monday (new week).
    times = [_t(1, 5), _t(1, 7), _t(1, 8)]
    assert [policy.should_rebalance(_Ctx(t)) for t in times] == [True, False, True]


def test_periodic_rejects_unknown_period() -> None:
    with pytest.raises(ValueError):
        PeriodicRebalance("hourly")


def test_threshold_fires_only_beyond_max_drift() -> None:
    policy = ThresholdRebalance(max_drift=0.05)
    near = _Ctx(_t(1, 1), weights={"AAPL": 0.52}, targets={"AAPL": 0.5})
    far = _Ctx(_t(1, 1), weights={"AAPL": 0.58}, targets={"AAPL": 0.5})
    assert not policy.should_rebalance(near)
    assert policy.should_rebalance(far)


def test_threshold_counts_untargeted_holdings_as_zero_target_only_if_targeted() -> None:
    policy = ThresholdRebalance(max_drift=0.05)
    # A held symbol with no target is unmanaged: rebalance would not touch it,
    # so it must not trigger one.
    ctx = _Ctx(_t(1, 1), weights={"AAPL": 0.5, "MSFT": 0.9}, targets={"AAPL": 0.5})
    assert not policy.should_rebalance(ctx)
    # A targeted symbol not yet held drifts by its full target.
    ctx2 = _Ctx(_t(1, 1), weights={}, targets={"AAPL": 0.5})
    assert policy.drift(ctx2) == 0.5
    assert policy.should_rebalance(ctx2)


def test_signal_policy_fires_when_targets_change() -> None:
    policy = SignalRebalance()
    empty = _Ctx(_t(1, 1))
    a = _Ctx(_t(1, 2), targets={"AAPL": 0.5})
    a_again = _Ctx(_t(1, 3), targets={"AAPL": 0.5})
    b = _Ctx(_t(1, 4), targets={"AAPL": 0.6})
    assert not policy.should_rebalance(empty)
    assert policy.should_rebalance(a)
    assert not policy.should_rebalance(a_again)
    assert policy.should_rebalance(b)


def test_monthly_policy_in_a_real_run() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    n = 61  # Jan 1 .. Mar 1
    ts = [start + timedelta(days=i) for i in range(n)]

    def frame(price: float) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "timestamp": ts,
                "open": [price] * n,
                "high": [price + 1] * n,
                "low": [price - 1] * n,
                "close": [price] * n,
                "volume": [1000.0] * n,
            }
        ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))

    frames = {"AAPL": frame(10.0), "MSFT": frame(20.0)}

    class Monthly(Strategy):
        def __init__(self) -> None:
            self.policy = PeriodicRebalance("monthly")
            self.fired_on: list[tuple[int, int]] = []

        def on_bar(self, ctx) -> None:
            ctx.target_weight("AAPL", 0.5)
            ctx.target_weight("MSFT", 0.5)
            if self.policy.should_rebalance(ctx):
                self.fired_on.append((ctx.time.month, ctx.time.day))
                ctx.rebalance()

    strategy = Monthly()
    result = run_portfolio_backtest(
        frames=frames,
        strategy=strategy,
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    assert strategy.fired_on == [(1, 1), (2, 1), (3, 1)]
    # Prices are flat, so only the initial rebalance actually trades.
    assert {f.fill_index for f in result.fills} == {1}
    assert result.equity_curve[-1].weights == {"AAPL": 0.5, "MSFT": 0.5}
