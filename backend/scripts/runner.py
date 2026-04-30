"""Subprocess-based runner for user Python scripts.

The runner is *not* a strong security boundary on its own. It raises the
cost of an escape via:
  - AST allow-list (rejects most known escape strings before compile),
  - `multiprocessing.spawn` so the child does not inherit parent FDs,
  - resource limits (memory/CPU) on POSIX,
  - socket monkeypatch to block network egress,
  - wallclock timeout enforced by the parent.

See `todo/indicator-system.md` §Security for the full threat model and the
hardening that lands in phase 6 (seccomp, unprivileged user, escape fuzz suite).
"""

from __future__ import annotations

import io
import logging
import multiprocessing as mp
import os
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout

import pandas as pd

from backend.scripts.ast_guard import ScriptValidationError, validate
from backend.scripts.display import DisplayCollector, DisplayError
from backend.scripts.output_models import RunResult
from backend.scripts.sandbox_globals import build_globals


logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 5.0
DEFAULT_MEMORY_MB = 512


def _apply_resource_limits(memory_mb: int) -> None:
    """Best-effort POSIX resource caps. Silently skipped where unsupported."""
    try:
        import resource

        mem_bytes = memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            pass
        try:
            # CPU-seconds upper bound — wallclock timeout is the real one.
            resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        except (ValueError, OSError):
            pass
    except ImportError:
        pass


def _block_network() -> None:
    """Replace the socket factory so user code can't open connections."""
    import socket

    def _denied(*_a, **_kw):
        raise OSError("network access is disabled in user scripts")

    socket.socket = _denied  # type: ignore[assignment]
    socket.create_connection = _denied  # type: ignore[assignment]


def _child_main(
    conn,  # multiprocessing.connection.Connection
    code: str,
    df: pd.DataFrame,
    memory_mb: int,
) -> None:
    """Top-level (picklable) entrypoint executed inside the spawned child."""
    _apply_resource_limits(memory_mb)
    _block_network()

    try:
        os.close(0)
    except OSError:
        pass

    collector = DisplayCollector()
    g = build_globals(df, collector)
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    payload: dict = {
        "status": "ok",
        "outputs": [],
        "stdout": "",
        "stderr": "",
    }
    try:
        compiled = compile(code, "<script>", "exec")
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exec(compiled, g)
        payload["outputs"] = [o.model_dump(mode="json") for o in collector.outputs]
    except DisplayError as e:
        payload["status"] = "error"
        stderr_buf.write(f"display error: {e}\n")
    except MemoryError:
        payload["status"] = "killed"
        stderr_buf.write("script exceeded memory limit\n")
    except SystemExit:
        payload["status"] = "killed"
        stderr_buf.write("script called sys.exit / exit()\n")
    except BaseException:
        payload["status"] = "error"
        stderr_buf.write(traceback.format_exc())

    payload["stdout"] = stdout_buf.getvalue()
    payload["stderr"] = stderr_buf.getvalue()

    try:
        conn.send(payload)
    except Exception:
        # Pipe might be closed on a parent timeout — nothing we can do.
        pass
    finally:
        conn.close()


def run_script(
    code: str,
    df: pd.DataFrame,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    memory_mb: int = DEFAULT_MEMORY_MB,
) -> RunResult:
    """Run user `code` against `df`. Returns a fully populated `RunResult`."""
    started = time.monotonic()
    try:
        validate(code)
    except ScriptValidationError as e:
        return RunResult(
            status="error",
            stderr=f"script rejected: {e}\n",
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )

    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(
        target=_child_main,
        args=(child_conn, code, df, memory_mb),
        daemon=True,
    )
    proc.start()
    # Close the child's end in the parent so we get EOF if the child exits.
    child_conn.close()

    payload: dict | None = None
    timed_out = False
    try:
        if parent_conn.poll(timeout_s):
            try:
                payload = parent_conn.recv()
            except EOFError:
                payload = None
        else:
            timed_out = True
    finally:
        parent_conn.close()
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=1.0)
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=1.0)
        else:
            proc.join(timeout=1.0)

    elapsed_ms = int((time.monotonic() - started) * 1000)

    if timed_out:
        return RunResult(
            status="timeout",
            stderr=f"script exceeded {timeout_s}s wallclock timeout\n",
            elapsed_ms=elapsed_ms,
        )

    if payload is None:
        return RunResult(
            status="killed",
            stderr=(
                f"script exited without returning a result "
                f"(exitcode={proc.exitcode})\n"
            ),
            elapsed_ms=elapsed_ms,
        )

    return RunResult(
        status=payload.get("status", "ok"),
        outputs=payload.get("outputs", []),
        stdout=payload.get("stdout", ""),
        stderr=payload.get("stderr", ""),
        elapsed_ms=elapsed_ms,
    )
