import dataclasses

from backend.backtesting.engine import run_backtest
from backend.backtesting.run_config import RunInputs
from backend.backtesting.run_snapshot import assemble_snapshot
from backend.backtesting.serialize import result_to_dict
from backend.tests._backtesting_fixtures import BuyAndHold, canonical_frame

_CODE = "def on_bar(ctx):\n    pass\n"


def _blob():
    return result_to_dict(
        run_backtest(
            frame=canonical_frame(), strategy=BuyAndHold(), starting_cash=1e4, seed=0
        )
    )


def test_assemble_single_run():
    blob = _blob()
    inputs = RunInputs(
        code=_CODE, params={"n": 5}, data_version="v1", seed=0, starting_cash=1e4
    )
    snap = assemble_snapshot(blob, inputs)

    assert snap.kind == "single"
    assert len(snap.run_id) == 64
    assert snap.strategy_code == _CODE
    assert snap.params == {"n": 5}
    assert snap.meta["run_id"] == snap.run_id
    assert snap.meta["ast_hash"]
    assert snap.meta["starting_cash"] == 1e4
    assert snap.metrics == blob["metrics"]
    assert set(snap.result_body) == {"orders", "fills", "equity", "trades"}
    assert snap.bars["kind"] == "single" and snap.bars["data"] == blob["bars"]


def test_identical_inputs_assemble_same_run_id():
    blob, inputs = (
        _blob(),
        RunInputs(code=_CODE, params={}, data_version="v1", seed=0, starting_cash=1e4),
    )
    assert (
        assemble_snapshot(blob, inputs).run_id
        == assemble_snapshot(_blob(), dataclasses.replace(inputs)).run_id
    )
