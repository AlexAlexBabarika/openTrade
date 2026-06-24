# backend/routes/run_routes.py
"""Read / compare / rerun / export / import endpoints for stored run snapshots.

Thin layer over backend.backtesting.run_store + the pure diff/rerun functions.
Runs are global and content-addressed; there is no per-user scoping here.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from backend.backtesting.run_diff import diff_runs
from backend.backtesting.run_id import run_status
from backend.backtesting.run_rerun import rerun
from backend.backtesting.run_store import (
    RunIntegrityError,
    RunStore,
    export_run,
    import_run,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtests/runs", tags=["runs"])

_RUN_STORE = RunStore.default()


def _read(run_id: str) -> dict:
    try:
        return _RUN_STORE.read(run_id)
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"run {run_id} not found") from e


@router.get("")
def list_runs() -> dict:
    return {"run_ids": _RUN_STORE.list_ids()}


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    blob = _read(run_id)
    blob["status"] = run_status(blob["meta"])
    return blob


@router.get("/{a}/compare/{b}")
def compare(a: str, b: str) -> dict:
    return diff_runs(_read(a), _read(b))


@router.post("/{run_id}/rerun")
async def rerun_run(run_id: str) -> dict:
    original = _read(run_id)
    try:
        new_id = await run_in_threadpool(rerun, _RUN_STORE, run_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    return {"run_id": new_id, "diff": diff_runs(original, _RUN_STORE.read(new_id))}


@router.get("/{run_id}/export")
def export(run_id: str) -> FileResponse:
    if not _RUN_STORE.exists(run_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"run {run_id} not found")
    dest = Path(tempfile.mkdtemp())
    tar = export_run(_RUN_STORE, run_id, dest)
    return FileResponse(
        tar,
        media_type="application/gzip",
        filename=tar.name,
        background=BackgroundTask(shutil.rmtree, dest, ignore_errors=True),
    )


@router.post("/import")
async def import_tarball(file: UploadFile) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        run_id = await run_in_threadpool(import_run, _RUN_STORE, tmp_path)
    except RunIntegrityError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"run_id": run_id}
