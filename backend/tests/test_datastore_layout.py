import polars as pl
from pathlib import Path
from backend.datastore.layout import StoreLayout

from backend.datastore.schema import (
    ACTIONS_SCHEMA,
    BARS_SCHEMA,
    MEMBERSHIP_SCHEMA,
    empty_frame,
)


def test_empty_frame_matches_schema():
    f = empty_frame(BARS_SCHEMA)
    assert f.height == 0
    assert f.schema["timestamp"] == pl.Datetime("us", "UTC")
    assert set(f.columns) == set(BARS_SCHEMA)


def test_actions_and_membership_columns():
    assert set(ACTIONS_SCHEMA) == {"symbol", "ex_date", "kind", "value"}
    assert set(MEMBERSHIP_SCHEMA) == {"index", "symbol", "start", "end"}


def test_layout_paths(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    assert (
        layout.bars("yfinance", "AAPL")
        == tmp_path / "bars" / "yfinance" / "AAPL.parquet"
    )
    assert (
        layout.actions("yfinance", "AAPL")
        == tmp_path / "actions" / "yfinance" / "AAPL.parquet"
    )
    assert layout.membership("SP500") == tmp_path / "membership" / "SP500.parquet"
    assert (
        layout.quarantine("yfinance", "AAPL")
        == tmp_path / "quarantine" / "yfinance" / "AAPL.parquet"
    )
    assert layout.manifest == tmp_path / "manifest.json"


def test_layout_ensure_dirs_creates_parents(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    p = layout.bars("yfinance", "AAPL")
    layout.ensure_parent(p)
    assert p.parent.is_dir()


def test_default_root_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENTRADE_DATA_ROOT", str(tmp_path / "store"))
    layout = StoreLayout.default()
    assert layout.root == tmp_path / "store"
