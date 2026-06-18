from pathlib import Path

from backend.datastore.layout import StoreLayout
from backend.datastore.manifest import (
    ManifestEntry,
    compute_version,
    file_checksum,
    load_manifest,
    write_entry,
)


def _write(p: Path, data: bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def test_checksum_stable_and_sensitive(tmp_path: Path):
    a = tmp_path / "a.bin"
    _write(a, b"hello")
    h1 = file_checksum(a)
    h2 = file_checksum(a)
    assert h1 == h2
    _write(a, b"hello!")
    assert file_checksum(a) != h1


def test_version_changes_only_when_inputs_change():
    cks = {"bars/yf/AAPL.parquet": "abc", "actions/yf/AAPL.parquet": "def"}
    v1 = compute_version(cks, adjust_logic_version="1")
    assert v1 == compute_version(
        dict(reversed(list(cks.items()))), adjust_logic_version="1"
    )
    assert v1 != compute_version(
        {**cks, "bars/yf/AAPL.parquet": "zzz"}, adjust_logic_version="1"
    )
    assert v1 != compute_version(cks, adjust_logic_version="2")


def test_write_and_load_roundtrip(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    entry = ManifestEntry(
        data_version="v1",
        symbols=["AAPL"],
        ranges={"AAPL": ("2020-01-01", "2020-12-31")},
        checksums={"bars/yf/AAPL.parquet": "abc"},
        adjust_logic_version="1",
        ingested_at="2026-06-16T00:00:00+00:00",
    )
    write_entry(layout, entry)
    loaded = load_manifest(layout)
    assert loaded["head"] == "v1"
    assert loaded["versions"]["v1"]["symbols"] == ["AAPL"]
