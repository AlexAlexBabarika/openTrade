# backend/tests/test_run_export.py
import json

import pytest

from backend.backtesting.engine import run_backtest
from backend.backtesting.run_config import RunInputs
from backend.backtesting.run_snapshot import assemble_snapshot
from backend.backtesting.run_store import (
    RunIntegrityError,
    RunStore,
    export_run,
    import_run,
)
from backend.backtesting.serialize import result_to_dict
from backend.tests._backtesting_fixtures import BuyAndHold, canonical_frame


def _write(store):
    blob = result_to_dict(
        run_backtest(
            frame=canonical_frame(), strategy=BuyAndHold(), starting_cash=1e4, seed=0
        )
    )
    return store.write(
        assemble_snapshot(
            blob,
            RunInputs(
                code="def on_bar(ctx):\n    pass\n",
                params={},
                data_version="v1",
                seed=0,
                starting_cash=1e4,
            ),
        )
    )


def test_export_then_import_round_trips(tmp_path):
    src = RunStore(tmp_path / "a")
    rid = _write(src)
    tar = export_run(src, rid, tmp_path)
    assert tar.exists()

    dst = RunStore(tmp_path / "b")
    assert import_run(dst, tar) == rid
    assert dst.read(rid)["meta"]["run_id"] == rid


def test_import_rejects_tampered_tarball(tmp_path):
    src = RunStore(tmp_path / "a")
    rid = _write(src)
    # tamper: change a param without updating meta -> run_id no longer matches contents
    params_path = src.path(rid) / "params.json"
    params_path.write_text(json.dumps({"n": 999}))
    tar = export_run(src, rid, tmp_path)

    dst = RunStore(tmp_path / "b")
    with pytest.raises(RunIntegrityError):
        import_run(dst, tar)
