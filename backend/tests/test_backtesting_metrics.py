"""The metrics taxonomy. Each group is a pure function tested against a small,
hand-computable fixture so every dashboard number is independently verifiable.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from backend.backtesting.types import EquityPoint


def _curve(values: list[float], *, step_days: int = 1) -> list[EquityPoint]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    pts = []
    for i, v in enumerate(values):
        pts.append(
            EquityPoint(
                time=start + timedelta(days=i * step_days),
                equity=v,
                cash=v,
                holdings=0.0,
            )
        )
    return pts


def test_total_return():
    from backend.backtesting.metrics import total_return

    assert math.isclose(total_return(_curve([100.0, 110.0, 121.0])), 0.21)


def test_cagr_one_year_doubles():
    from backend.backtesting.metrics import cagr

    # 100 -> 200 over exactly 365 days ~= 100% CAGR.
    curve = _curve([100.0, 200.0], step_days=365)
    assert math.isclose(cagr(curve), 1.0, rel_tol=1e-3)


def test_period_returns_monthly_and_yearly():
    from backend.backtesting.metrics import monthly_returns, yearly_returns

    # Two months: Jan ends at 110 (from base 100), Feb ends at 99 (from 110).
    start = datetime(2024, 1, 31, tzinfo=timezone.utc)
    pts = [
        EquityPoint(time=start, equity=110.0, cash=110.0, holdings=0.0),
        EquityPoint(
            time=datetime(2024, 2, 29, tzinfo=timezone.utc),
            equity=99.0,
            cash=99.0,
            holdings=0.0,
        ),
    ]
    # First period uses the first point's own equity as its base.
    m = monthly_returns(pts)
    assert math.isclose(m[0], 0.0)  # 110 / 110 - 1
    assert math.isclose(m[1], -0.1)  # 99 / 110 - 1

    y = yearly_returns(_curve([100.0, 100.0, 125.0]))  # all in 2024
    assert math.isclose(y[0], 0.25)  # 125 / 100 - 1


def test_positive_period_fractions():
    from backend.backtesting.metrics import pct_positive

    assert pct_positive([0.1, -0.2, 0.3, 0.0]) == 0.5  # 2 of 4 strictly > 0


# --- Task 4: Risk-adjusted metrics ---


def test_sharpe_zero_when_no_volatility():
    from backend.backtesting.metrics import sharpe

    # Constant 1% per period -> zero stdev -> Sharpe defined as 0.
    rets = [0.01] * 10
    assert sharpe(rets, risk_free_rate=0.0, periods_per_year=252.0) == 0.0


def test_sharpe_known_value():
    from backend.backtesting.metrics import sharpe

    rets = [0.01, -0.01, 0.02, -0.02]
    # mean = 0; with rf=0 the numerator is 0 -> Sharpe 0.
    assert sharpe(rets, risk_free_rate=0.0, periods_per_year=252.0) == 0.0

    rets2 = [0.02, 0.00, 0.04, 0.02]  # mean 0.02, sample stdev ~0.01633
    val = sharpe(rets2, risk_free_rate=0.0, periods_per_year=252.0)
    assert val > 0


def test_sortino_ignores_upside_volatility():
    from backend.backtesting.metrics import sortino

    # No negative returns -> downside deviation 0 -> Sortino defined as 0.
    assert (
        sortino([0.01, 0.02, 0.03], risk_free_rate=0.0, periods_per_year=252.0) == 0.0
    )


def test_calmar_is_cagr_over_max_dd():
    from backend.backtesting.metrics import calmar

    assert math.isclose(calmar(cagr_value=0.2, max_drawdown=-0.1), 2.0)
    assert calmar(cagr_value=0.2, max_drawdown=0.0) == 0.0


def test_information_ratio_zero_when_tracking_benchmark():
    from backend.backtesting.metrics import information_ratio

    rets = [0.01, 0.02, -0.01]
    assert information_ratio(rets, rets, periods_per_year=252.0) == 0.0


# --- Task 5: Drawdown metrics ---


def test_drawdown_episodes_and_summary():
    from backend.backtesting.metrics import compute_drawdowns

    # 100 -> 120 (peak) -> 90 (trough) -> 120 (recovers) -> 130.
    curve = _curve([100.0, 120.0, 90.0, 120.0, 130.0])
    episodes = compute_drawdowns(curve)

    assert len(episodes) == 1
    (dd,) = episodes
    assert math.isclose(dd.depth, 90.0 / 120.0 - 1)  # -0.25
    assert dd.recovery is not None
    assert dd.length == 2  # peak idx 1 -> recovery idx 3


def test_unrecovered_drawdown_has_no_recovery():
    from backend.backtesting.metrics import compute_drawdowns

    curve = _curve([100.0, 80.0, 90.0])  # never regains 100
    (dd,) = compute_drawdowns(curve)
    assert dd.recovery is None
    assert math.isclose(dd.depth, -0.2)


def test_max_and_avg_drawdown():
    from backend.backtesting.metrics import compute_drawdowns, max_drawdown

    curve = _curve([100.0, 90.0, 100.0, 50.0, 100.0])  # -0.1 then -0.5
    episodes = compute_drawdowns(curve)
    assert math.isclose(max_drawdown(episodes), -0.5)


def test_time_underwater():
    from backend.backtesting.metrics import time_underwater

    curve = _curve([100.0, 90.0, 90.0, 100.0])  # 2 of 4 points below running peak
    assert time_underwater(curve) == 0.5


# --- Task 6: Trade-quality metrics ---


def _trade(*, pnl: float, bars_held: int = 1):
    from backend.backtesting.types import Side, Trade

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return Trade(
        direction=Side.BUY,
        quantity=1.0,
        entry_time=start,
        exit_time=start + timedelta(days=bars_held),
        entry_index=0,
        exit_index=bars_held,
        entry_price=100.0,
        exit_price=100.0 + pnl,
        pnl=pnl,
        pnl_pct=pnl / 100.0,
        bars_held=bars_held,
    )


def test_trade_quality_basics():
    from backend.backtesting.metrics import trade_quality

    trades = [_trade(pnl=10.0), _trade(pnl=-5.0), _trade(pnl=20.0), _trade(pnl=-5.0)]
    q = trade_quality(trades)

    assert q["win_rate"] == 0.5
    assert q["avg_win"] == 15.0  # (10 + 20) / 2
    assert q["avg_loss"] == -5.0
    assert q["win_loss_ratio"] == 3.0  # 15 / 5
    assert q["profit_factor"] == 3.0  # 30 / 10
    assert q["expectancy"] == 5.0  # (10 -5 +20 -5) / 4


def test_max_consecutive_runs():
    from backend.backtesting.metrics import trade_quality

    trades = [
        _trade(pnl=1.0),
        _trade(pnl=1.0),
        _trade(pnl=-1.0),
        _trade(pnl=-1.0),
        _trade(pnl=-1.0),
        _trade(pnl=1.0),
    ]
    q = trade_quality(trades)
    assert q["max_consecutive_wins"] == 2
    assert q["max_consecutive_losses"] == 3


def test_trade_quality_empty_is_none():
    from backend.backtesting.metrics import trade_quality

    q = trade_quality([])
    assert q["win_rate"] is None
    assert q["profit_factor"] is None
    assert q["max_consecutive_wins"] == 0


# --- Task 7: Exposure metrics ---


def test_exposure_metrics():
    from backend.backtesting.metrics import exposure
    from backend.backtesting.types import EquityPoint

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    pts = [
        EquityPoint(time=start, equity=1000.0, cash=1000.0, holdings=0.0),
        EquityPoint(
            time=start + timedelta(days=1), equity=1000.0, cash=500.0, holdings=500.0
        ),
        EquityPoint(
            time=start + timedelta(days=2), equity=1000.0, cash=0.0, holdings=1000.0
        ),
    ]
    e = exposure(pts)

    assert math.isclose(e["pct_time_in_market"], 2 / 3)  # 2 of 3 points hold
    assert math.isclose(e["avg_position_pct"], (0.0 + 0.5 + 1.0) / 3)
    assert math.isclose(e["max_leverage"], 1.0)


def test_exposure_handles_short_holdings():
    from backend.backtesting.metrics import exposure
    from backend.backtesting.types import EquityPoint

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    pts = [EquityPoint(time=start, equity=1000.0, cash=2000.0, holdings=-1000.0)]
    e = exposure(pts)
    assert e["pct_time_in_market"] == 1.0
    assert math.isclose(e["max_leverage"], 1.0)  # |−1000| / 1000


# --- Task 8: compute_metrics orchestrator ---


def test_compute_metrics_assembles_full_taxonomy():
    from backend.backtesting.metrics import compute_metrics
    from backend.backtesting.types import Bar, Metrics

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    closes = [100.0, 110.0, 105.0, 120.0]
    bars = [
        Bar(
            time=start + timedelta(days=i),
            open=c,
            high=c + 1,
            low=c - 1,
            close=c,
            volume=1.0,
        )
        for i, c in enumerate(closes)
    ]
    curve = _curve(closes)  # equity mirrors price here, 1:1 with bars
    trades = [_trade(pnl=10.0), _trade(pnl=-5.0)]

    m = compute_metrics(curve, trades, bars)

    assert isinstance(m, Metrics)
    assert math.isclose(m.total_return, 0.2)  # 120 / 100 - 1
    assert m.win_rate == 0.5
    assert m.max_drawdown < 0  # there is a dip to 105
    # Strategy returns == benchmark returns here -> IR is 0.
    assert m.information_ratio == 0.0


def test_compute_metrics_with_no_trades():
    from backend.backtesting.metrics import compute_metrics
    from backend.backtesting.types import Bar

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    closes = [100.0, 101.0, 102.0]
    bars = [
        Bar(time=start + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1.0)
        for i, c in enumerate(closes)
    ]
    m = compute_metrics(_curve(closes), [], bars)
    assert m.win_rate is None
    assert m.max_consecutive_wins == 0
    assert m.pct_time_in_market == 0.0  # _curve has holdings 0 throughout
