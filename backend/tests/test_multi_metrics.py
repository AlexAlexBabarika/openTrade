"""
Portfolio metrics extend the single-run taxonomy with what only exists at the
portfolio level: concentration (HHI, top-5, max single name), sector exposure
over time, pairwise correlation of position-contribution returns, turnover,
and P&L attribution by symbol/sector — with the portfolio Sharpe reported
alongside individual-symbol Sharpes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from backend.backtesting.costs import Costs
from backend.backtesting.multi.book import PortfolioEquityPoint
from backend.backtesting.multi.engine import run_portfolio_backtest
from backend.backtesting.multi.metrics import (
    PortfolioMetrics,
    attribution_by_symbol,
    concentration,
    contribution_series,
    pairwise_correlation,
    sector_exposure_over_time,
    symbol_sharpes,
)
from backend.backtesting.multi.timeline import events_from_frames
from backend.backtesting.strategy import Strategy
from backend.backtesting.types import Fill, Side

_T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _point(
    day: int, weights: dict[str, float], equity: float = 1_000.0
) -> PortfolioEquityPoint:
    holdings = sum(weights.values()) * equity
    return PortfolioEquityPoint(
        time=_T0 + timedelta(days=day),
        equity=equity,
        cash=equity - holdings,
        holdings=holdings,
        weights=weights,
    )


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


def _fill(
    symbol: str, side: Side, qty: float, price: float, commission: float = 0.0
) -> Fill:
    return Fill(
        order_id=0,
        side=side,
        quantity=qty,
        price=price,
        reference_price=price,
        slippage=0.0,
        spread_cost=0.0,
        commission=commission,
        submitted_index=0,
        fill_index=1,
        reason="market",
        symbol=symbol,
    )


def test_concentration_summarizes_hhi_top5_and_single_name() -> None:
    curve = [
        _point(0, {}),  # flat start
        _point(1, {"A": 0.5, "B": 0.5}),
        _point(2, {"A": 0.8, "B": 0.1, "C": 0.1, "D": 0.1, "E": 0.1, "F": 0.1}),
    ]
    stats = concentration(curve)
    # Point 1 HHI = 0.5; point 2 HHI = 0.64 + 5*0.01 = 0.69.
    assert stats["max_hhi"] == pytest.approx(0.69)
    assert stats["avg_hhi"] == pytest.approx((0.0 + 0.5 + 0.69) / 3)
    # Top-5 at point 2: 0.8 + 4*0.1 = 1.2 (six names, one falls outside).
    assert stats["max_top5_weight"] == pytest.approx(1.2)
    assert stats["max_single_name_weight"] == pytest.approx(0.8)


def test_concentration_uses_absolute_weights_for_shorts() -> None:
    curve = [_point(0, {"A": 0.5, "B": -0.5})]
    stats = concentration(curve)
    assert stats["max_hhi"] == pytest.approx(0.5)
    assert stats["max_top5_weight"] == pytest.approx(1.0)


def test_contribution_series_is_lagged_weight_times_price_return() -> None:
    # A: 10 -> 11 (+10%) -> 11; B: flat 20.
    events = events_from_frames(
        {"A": _frame([10.0, 11.0, 11.0]), "B": _frame([20.0, 20.0, 20.0])}
    )
    curve = [
        _point(0, {"A": 0.5, "B": 0.5}),
        _point(1, {"A": 0.54, "B": 0.5}),
        _point(2, {"A": 0.54, "B": 0.5}),
    ]
    series = contribution_series(events, curve)
    assert series["A"] == [pytest.approx(0.05), 0.0]  # 0.5 * 10%, then flat
    assert series["B"] == [0.0, 0.0]


def test_pairwise_correlation_of_contributions() -> None:
    series = {
        "A": [0.01, -0.02, 0.03, -0.01],
        "B": [0.02, -0.04, 0.06, -0.02],  # 2x A: perfectly correlated
        "C": [-0.01, 0.02, -0.03, 0.01],  # -1x A: perfectly anticorrelated
        "D": [0.0, 0.0, 0.0, 0.0],  # never contributes
    }
    symbols, matrix = pairwise_correlation(series)
    assert symbols == ["A", "B", "C", "D"]
    i, j, k, d = 0, 1, 2, 3
    assert matrix[i][i] == 1.0
    assert matrix[i][j] == pytest.approx(1.0)
    assert matrix[i][k] == pytest.approx(-1.0)
    assert matrix[i][d] == 0.0  # zero variance -> defined as 0
    assert matrix[j][i] == matrix[i][j]


def test_sector_exposure_over_time() -> None:
    curve = [
        _point(0, {"AAPL": 0.3, "MSFT": 0.2, "XOM": -0.1}),
        _point(1, {"AAPL": 0.4}),
    ]
    sectors = {"AAPL": "tech", "MSFT": "tech", "XOM": "energy"}
    exposure = sector_exposure_over_time(curve, sectors)
    assert len(exposure) == 2
    assert exposure[0].exposures == {"tech": pytest.approx(0.5), "energy": -0.1}
    assert exposure[1].exposures == {"tech": pytest.approx(0.4)}
    assert sector_exposure_over_time(curve, None) == []


def test_attribution_by_symbol_from_fills_and_final_marks() -> None:
    fills = [
        _fill("A", Side.BUY, 10.0, 10.0, commission=1.0),
        _fill("A", Side.SELL, 10.0, 12.0, commission=1.0),  # closed: +20 - 2
        _fill("B", Side.BUY, 5.0, 10.0, commission=1.0),  # open, marked at 12
    ]
    attr = attribution_by_symbol(fills, {"A": 12.0, "B": 12.0})
    assert attr["A"] == pytest.approx(18.0)
    assert attr["B"] == pytest.approx(5.0 * 12.0 - 50.0 - 1.0)


def test_symbol_sharpes_distinguish_trending_from_flat() -> None:
    events = events_from_frames(
        {
            "UP": _frame([100.0 * 1.01**i for i in range(20)]),
            "FLAT": _frame([100.0] * 20),
        }
    )
    sharpes = symbol_sharpes(events)
    assert sharpes["UP"] > 1.0
    assert sharpes["FLAT"] == 0.0


def test_engine_result_carries_portfolio_metrics() -> None:
    frames = {
        "AAPL": _frame([10.0, 10.5, 10.2, 10.8, 11.0]),
        "MSFT": _frame([20.0, 19.5, 20.5, 20.2, 21.0]),
    }

    class FiftyFifty(Strategy):
        def on_bar(self, ctx) -> None:
            if ctx.time.day == 1:
                ctx.target_weight("AAPL", 0.5)
                ctx.target_weight("MSFT", 0.5)
                ctx.rebalance()

    result = run_portfolio_backtest(
        frames=frames,
        strategy=FiftyFifty(),
        starting_cash=1_000.0,
        costs=Costs.frictionless(),
    )
    m = result.metrics
    assert isinstance(m, PortfolioMetrics)
    # Portfolio Sharpe alongside individual-symbol Sharpes (acceptance).
    assert isinstance(m.portfolio.sharpe, float)
    assert set(m.symbol_sharpes) == {"AAPL", "MSFT"}
    assert m.turnover_annualized > 0.0
    assert set(m.turnover_per_event) == {1}
    assert set(m.attribution_by_symbol) == {"AAPL", "MSFT"}
    assert m.correlation_symbols == ["AAPL", "MSFT"]
    assert m.max_single_name_weight > 0.4
    # P&L attribution reconciles with the equity curve.
    total_pnl = result.equity_curve[-1].equity - 1_000.0
    assert sum(m.attribution_by_symbol.values()) == pytest.approx(total_pnl)
