# backend/tests/test_reproducibility_acceptance.py
"""Acceptance: maps to todo/backtesting-platform/06-reproducibility.md."""

from backend.backtesting import version as ver
from backend.backtesting.engine import run_backtest
from backend.backtesting.run_config import RunInputs
from backend.backtesting.run_diff import diff_runs
from backend.backtesting.run_id import run_status
from backend.backtesting.run_rerun import rerun
from backend.backtesting.run_snapshot import assemble_snapshot
from backend.backtesting.run_store import RunStore, export_run, import_run
from backend.backtesting.serialize import result_to_dict
from backend.tests._backtesting_fixtures import BuyAndHold, canonical_frame

_CODE = "def on_bar(ctx):\n    pass\n"


def _snapshot(store, *, params, seed=0):
    blob = result_to_dict(
        run_backtest(
            frame=canonical_frame(), strategy=BuyAndHold(), starting_cash=1e4, seed=seed
        )
    )
    return store.write(
        assemble_snapshot(
            blob,
            RunInputs(
                code=_CODE,
                params=params,
                data_version="v1",
                seed=seed,
                starting_cash=1e4,
            ),
        )
    )


def test_criterion_reproducible_or_flagged(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    rid = _snapshot(store, params={"n": 10})
    # Re-run on the same engine -> byte-identical metrics + same id.
    assert rerun(store, rid) == rid
    assert (
        store.read(rid)["metrics"]
        == result_to_dict(
            run_backtest(
                frame=canonical_frame(),
                strategy=BuyAndHold(),
                starting_cash=1e4,
                seed=0,
            )
        )["metrics"]
    )
    # Bump engine -> read flags stale (without recomputing the stored numbers).
    monkeypatch.setattr(ver, "ENGINE_VERSION", "1.1.0")
    monkeypatch.setattr("backend.backtesting.run_id.ENGINE_VERSION", "1.1.0")
    status = run_status(store.read(rid)["meta"])
    assert status == {"stale": True, "recorded": "1.0.0", "current": "1.1.0"}


def test_criterion_single_param_diff(tmp_path):
    store = RunStore(tmp_path)
    a, b = _snapshot(store, params={"n": 10}), _snapshot(store, params={"n": 20})
    diff = diff_runs(store.read(a), store.read(b))
    assert [r["path"] for r in diff["inputs_diff"]] == ["params.n"]


def test_criterion_tarball_shareable(tmp_path):
    src = RunStore(tmp_path / "mine")
    rid = _snapshot(src, params={"n": 10})
    tar = export_run(src, rid, tmp_path)
    teammate = RunStore(tmp_path / "theirs")
    assert import_run(teammate, tar) == rid
    assert rerun(teammate, rid) == rid  # re-runs offline from the tarball's own bars
