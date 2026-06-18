from datetime import datetime, timezone
from pathlib import Path

from backend.datastore.layout import StoreLayout
from backend.datastore.membership import (
    SEED_DIR,
    load_seed,
    read_membership,
    resolve_universe,
    write_membership,
)


def _utc(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def test_load_seed_has_expected_columns():
    f = load_seed(SEED_DIR / "sp500_membership.csv")
    assert set(f.columns) == {"index", "symbol", "start", "end"}
    assert f.height >= 7


def test_resolve_universe_differs_2010_vs_today(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    write_membership(layout, "SP500", load_seed(SEED_DIR / "sp500_membership.csv"))

    u2010 = resolve_universe(layout, "SP500", _utc(2010, 6, 1), _utc(2010, 6, 2))
    u2026 = resolve_universe(layout, "SP500", _utc(2026, 6, 1), _utc(2026, 6, 2))

    s2010, s2026 = set(u2010.symbols), set(u2026.symbols)
    # AC#1: the two universes are different.
    assert s2010 != s2026
    assert "EK" in s2010 and "EK" not in s2026  # left in 2011
    assert "TSLA" in s2026 and "TSLA" not in s2010  # joined 2020
    assert "DELL" in s2010 and "DELL" in s2026  # member in both windows


def test_resolve_universe_respects_active_at_time(tmp_path: Path):
    layout = StoreLayout(root=tmp_path)
    write_membership(layout, "SP500", load_seed(SEED_DIR / "sp500_membership.csv"))
    # DELL was private 2013-10-30 .. 2024-09-23: not active mid-2015.
    u = resolve_universe(layout, "SP500", _utc(2015, 6, 1), _utc(2015, 6, 2))
    assert not u.is_active("DELL", _utc(2015, 6, 1))


def test_read_membership_missing_raises(tmp_path: Path):
    import pytest

    from backend.datastore.errors import DataNotFound

    layout = StoreLayout(root=tmp_path)
    with pytest.raises(DataNotFound):
        read_membership(layout, "NOPE")
