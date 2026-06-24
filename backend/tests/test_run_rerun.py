# backend/tests/test_run_rerun.py
import pytest

from backend.backtesting.engine import run_backtest
from backend.backtesting.run_config import RunInputs
from backend.backtesting.run_rerun import frame_from_bars, rerun
from backend.backtesting.run_snapshot import assemble_snapshot
from backend.backtesting.run_store import RunStore
from backend.backtesting.serialize import result_to_dict
from backend.tests._backtesting_fixtures import canonical_frame

# A strategy whose code is stored verbatim in the snapshot and re-run from it.
_CODE = "def on_bar(ctx):\n    if ctx.bars.index == 0:\n        ctx.buy(1.0)\n"


def _store_initial_run(tmp_path):
    # Run the engine the same way the sandbox child does, then snapshot it.
    from backend.backtesting.sandbox import run_strategy

    frame = canonical_frame()
    res = run_strategy(_CODE, frame, starting_cash=1e4, seed=0)
    blob = {
        "meta": res.meta,
        "bars": res.bars,
        "orders": res.orders,
        "fills": res.fills,
        "equity": res.equity,
        "trades": res.trades,
        "metrics": res.metrics,
    }
    store = RunStore(tmp_path)
    rid = store.write(
        assemble_snapshot(
            blob,
            RunInputs(
                code=_CODE, params={}, data_version="v1", seed=0, starting_cash=1e4
            ),
        )
    )
    return store, rid


def test_frame_from_bars_rebuilds_engine_schema():
    blob = result_to_dict(
        run_backtest(
            frame=canonical_frame(),
            strategy=__import__(
                "backend.tests._backtesting_fixtures", fromlist=["BuyAndHold"]
            ).BuyAndHold(),
            starting_cash=1e4,
            seed=0,
        )
    )
    frame = frame_from_bars(blob["bars"])
    assert frame.columns[:6] == ["timestamp", "open", "high", "low", "close", "volume"]
    assert frame.height == len(blob["bars"])


def test_rerun_reproduces_metrics_and_id(tmp_path):
    store, rid = _store_initial_run(tmp_path)
    new_rid = rerun(store, rid)
    assert new_rid == rid  # same engine version + same inputs -> same content id
    assert store.read(new_rid)["metrics"] == store.read(rid)["metrics"]


_RAISING_CODE = "def on_bar(ctx):\n    raise ValueError('boom')\n"


def test_rerun_raises_when_strategy_fails(tmp_path):
    """Rerun raises ValueError when the replayed strategy errors at runtime."""
    # First, store a valid snapshot (needs real meta with engine_version etc.)
    store, rid = _store_initial_run(tmp_path)
    # Now overwrite strategy.py on disk with code that raises
    (store.path(rid) / "strategy.py").write_text(_RAISING_CODE)
    with pytest.raises(ValueError, match="rerun failed"):
        rerun(store, rid)
