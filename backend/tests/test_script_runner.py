"""Phase 1 verification for the user-script runner.

Covers the three checks the plan calls out:
  - SMA script returns a serialized overlay,
  - infinite loop is killed at `timeout_s`,
  - `import os; os.system(...)` is rejected by the AST guard before compile.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.scripts.runner import run_script


@pytest.fixture
def df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=60, freq="1D", tz="UTC")
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.standard_normal(60))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.full(60, 1000.0),
        },
        index=idx,
    )


def test_sma_overlay(df: pd.DataFrame) -> None:
    code = "display.line(price.rolling(20).mean(), title='SMA20')"
    res = run_script(code, df, timeout_s=10.0)
    assert res.status == "ok", res.stderr
    assert len(res.outputs) == 1
    out = res.outputs[0]
    assert out.type == "overlay"
    assert out.title == "SMA20"
    assert len(out.data) > 0
    for p in out.data:
        assert isinstance(p.time, int)
        assert isinstance(p.value, float)


def test_infinite_loop_times_out(df: pd.DataFrame) -> None:
    code = "while True:\n    pass\n"
    res = run_script(code, df, timeout_s=1.0)
    assert res.status == "timeout"


def test_ast_rejects_import_os(df: pd.DataFrame) -> None:
    code = "import os\nos.system('ls')\n"
    res = run_script(code, df, timeout_s=2.0)
    assert res.status == "error"
    assert "not allowed" in res.stderr


def test_ast_rejects_dunder_escape(df: pd.DataFrame) -> None:
    code = "().__class__.__bases__[0].__subclasses__()\n"
    res = run_script(code, df, timeout_s=2.0)
    assert res.status == "error"
    assert "not allowed" in res.stderr
