"""
Hard portfolio constraints are enforced at order generation: rebalance()
clamps the effective target weights before diffing, so no order it submits
can violate them, and every binding is logged as a structured event the user
can audit ("wanted 5% AAPL, capped at 3%..."). The no-trade list also blocks
direct ctx.buy/sell. Constraints clamp a copy — the strategy's declared
targets persist unmodified.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from backend.backtesting.costs import Costs
from backend.backtesting.errors import ConstraintError
from backend.backtesting.multi.constraints import (
    ConstraintEvent,
    Constraints,
    apply_constraints,
)
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.strategy import Strategy

_T = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _apply(targets, constraints, equity=1_000.0):
    return apply_constraints(targets, constraints=constraints, equity=equity, time=_T)


def test_max_position_weight_clamps_and_logs() -> None:
    clamped, events = _apply(
        {"AAPL": 0.5, "MSFT": 0.2}, Constraints(max_position_weight=0.3)
    )
    assert clamped == {"AAPL": 0.3, "MSFT": 0.2}
    assert len(events) == 1
    e = events[0]
    assert isinstance(e, ConstraintEvent)
    assert (e.constraint, e.symbol) == ("max_position_weight", "AAPL")
    assert (e.requested, e.applied) == (0.5, 0.3)
    assert "AAPL" in e.detail


def test_max_position_weight_clamps_shorts_by_magnitude() -> None:
    clamped, events = _apply({"AAPL": -0.5}, Constraints(max_position_weight=0.3))
    assert clamped == {"AAPL": -0.3}


def test_max_position_value_converts_dollars_to_weight() -> None:
    clamped, events = _apply(
        {"AAPL": 0.5}, Constraints(max_position_value=100.0), equity=1_000.0
    )
    assert clamped == {"AAPL": 0.1}
    assert events[0].constraint == "max_position_value"


def test_long_only_zeroes_shorts() -> None:
    clamped, events = _apply({"AAPL": 0.5, "MSFT": -0.3}, Constraints(long_only=True))
    assert clamped == {"AAPL": 0.5, "MSFT": 0.0}
    assert [(e.constraint, e.symbol) for e in events] == [("long_only", "MSFT")]


def test_no_short_list_zeroes_only_listed_symbols() -> None:
    clamped, events = _apply(
        {"AAPL": -0.2, "MSFT": -0.3}, Constraints(no_short=frozenset({"MSFT"}))
    )
    assert clamped == {"AAPL": -0.2, "MSFT": 0.0}
    assert [(e.constraint, e.symbol) for e in events] == [("no_short", "MSFT")]


def test_no_trade_list_drops_the_target() -> None:
    clamped, events = _apply(
        {"AAPL": 0.5, "MSFT": 0.5}, Constraints(no_trade=frozenset({"MSFT"}))
    )
    assert clamped == {"AAPL": 0.5}
    e = events[0]
    assert (e.constraint, e.symbol, e.applied) == ("no_trade", "MSFT", None)


def test_sector_cap_scales_members_proportionally() -> None:
    constraints = Constraints(
        max_sector_weight=0.3,
        sectors={"AAPL": "tech", "MSFT": "tech", "XOM": "energy"},
    )
    clamped, events = _apply({"AAPL": 0.4, "MSFT": 0.2, "XOM": 0.2}, constraints)
    # Tech gross 0.6 -> scaled by 0.5; energy under its cap, untouched.
    assert clamped == {
        "AAPL": pytest.approx(0.2),
        "MSFT": pytest.approx(0.1),
        "XOM": 0.2,
    }
    assert {(e.constraint, e.symbol) for e in events} == {
        ("max_sector_weight", "AAPL"),
        ("max_sector_weight", "MSFT"),
    }
    assert all("tech" in e.detail for e in events)


def test_symbols_without_a_sector_are_exempt_from_sector_caps() -> None:
    constraints = Constraints(max_sector_weight=0.1, sectors={"AAPL": "tech"})
    clamped, events = _apply({"AAPL": 0.4, "ZZZ": 0.4}, constraints)
    assert clamped == {"AAPL": pytest.approx(0.1), "ZZZ": 0.4}


def test_max_gross_scales_everything_with_one_aggregate_event() -> None:
    clamped, events = _apply({"AAPL": 1.0, "MSFT": -1.0}, Constraints(max_gross=1.0))
    assert clamped == {"AAPL": pytest.approx(0.5), "MSFT": pytest.approx(-0.5)}
    assert [(e.constraint, e.symbol) for e in events] == [("max_gross", None)]
    assert (events[0].requested, events[0].applied) == (2.0, 1.0)


def test_max_net_scales_the_dominant_side() -> None:
    # Net +0.6 with cap 0.0 (market-neutral): longs scale to match shorts.
    clamped, events = _apply({"AAPL": 0.8, "MSFT": -0.2}, Constraints(max_net=0.0))
    assert clamped == {"AAPL": pytest.approx(0.2), "MSFT": -0.2}
    assert events[0].constraint == "max_net"
    # Net short beyond the cap scales shorts.
    clamped2, _ = _apply({"AAPL": -0.8, "MSFT": 0.2}, Constraints(max_net=0.0))
    assert clamped2 == {"AAPL": pytest.approx(-0.2), "MSFT": 0.2}


def test_nothing_binds_nothing_logged() -> None:
    constraints = Constraints(
        max_position_weight=0.5,
        long_only=True,
        max_gross=2.0,
        max_net=1.0,
    )
    clamped, events = _apply({"AAPL": 0.3, "MSFT": 0.2}, constraints)
    assert clamped == {"AAPL": 0.3, "MSFT": 0.2}
    assert events == []


def _frame(price: float, n: int = 5) -> pl.DataFrame:
    ts = [_T + timedelta(days=i) for i in range(n)]
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


def test_rebalance_enforces_constraints_and_result_carries_the_log() -> None:
    frames = {"AAPL": _frame(10.0), "MSFT": _frame(20.0)}

    class Greedy(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("AAPL", 0.8)
                ctx.target_weight("MSFT", 0.1)
                ctx.rebalance()

    result = run_portfolio_backtest(
        frames=frames,
        strategy=Greedy(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
        constraints=Constraints(max_position_weight=0.25),
    )
    assert result.equity_curve[-1].weights == {
        "AAPL": pytest.approx(0.25),
        "MSFT": pytest.approx(0.1),
    }
    assert [(e.constraint, e.symbol) for e in result.constraint_events] == [
        ("max_position_weight", "AAPL")
    ]
    # The strategy's declared targets are not rewritten by enforcement.


def test_direct_orders_on_no_trade_symbols_are_blocked() -> None:
    frames = {"AAPL": _frame(10.0)}

    class Sneaky(Strategy):
        def on_bar(self, ctx) -> None:
            with pytest.raises(ConstraintError):
                ctx.buy("AAPL", 1.0)

    run_portfolio_backtest(
        frames=frames,
        strategy=Sneaky(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
        constraints=Constraints(no_trade=frozenset({"AAPL"})),
    )


def test_constraint_min_trade_value_skips_and_logs() -> None:
    # Day 3: AAPL ticks 10.00 -> 10.01, a ~$0.5 drift on a $500 position.
    frames = {
        "AAPL": pl.DataFrame(
            {
                "timestamp": [_T + timedelta(days=i) for i in range(4)],
                "open": [10.0, 10.0, 10.01, 10.01],
                "high": [11.0] * 4,
                "low": [9.0] * 4,
                "close": [10.0, 10.0, 10.01, 10.01],
                "volume": [1000.0] * 4,
            }
        ).with_columns(pl.col("timestamp").dt.replace_time_zone("UTC"))
    }

    class Steady(Strategy):
        def on_bar(self, ctx) -> None:
            ctx.target_weight("AAPL", 0.5)
            ctx.rebalance()

    result = run_portfolio_backtest(
        frames=frames,
        strategy=Steady(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
        constraints=Constraints(min_trade_value=10.0),
    )
    # Only the initial allocation traded.
    assert {f.fill_index for f in result.fills} == {1}
    skips = [e for e in result.constraint_events if e.constraint == "min_trade_value"]
    assert len(skips) >= 1
    assert all(e.applied is None for e in skips)
