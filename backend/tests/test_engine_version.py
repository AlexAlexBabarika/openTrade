from backend.backtesting.engine import run_backtest
from backend.backtesting.version import ENGINE_VERSION
from backend.tests._backtesting_fixtures import BuyAndHold, canonical_frame


def test_engine_version_is_semver():
    parts = ENGINE_VERSION.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_run_stamps_engine_version_into_meta():
    result = run_backtest(
        frame=canonical_frame(), strategy=BuyAndHold(), starting_cash=10_000.0, seed=0
    )
    assert result.meta.engine_version == ENGINE_VERSION
