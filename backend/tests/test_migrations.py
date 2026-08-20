from pathlib import Path

import pytest

from backend.core.migrations import _legacy_schema_state, discover_migrations


class _Cursor:
    def __init__(self, present: list[bool]) -> None:
        self.present = present

    def execute(self, _query: str) -> None:
        pass

    def fetchone(self) -> dict[str, list[bool]]:
        return {"present": self.present}


def test_discovers_migrations_in_numeric_order(tmp_path: Path) -> None:
    (tmp_path / "010_second.sql").write_text("SELECT 10;\n")
    (tmp_path / "002_first.sql").write_text("SELECT 2;\n")

    migrations = discover_migrations(tmp_path)

    assert [migration.version for migration in migrations] == [2, 10]
    assert [migration.name for migration in migrations] == ["first", "second"]
    assert all(len(migration.checksum) == 64 for migration in migrations)


def test_rejects_invalid_migration_filename(tmp_path: Path) -> None:
    (tmp_path / "initial.sql").write_text("SELECT 1;\n")

    with pytest.raises(RuntimeError, match="Invalid migration filename"):
        discover_migrations(tmp_path)


def test_rejects_duplicate_versions(tmp_path: Path) -> None:
    (tmp_path / "001_first.sql").write_text("SELECT 1;\n")
    (tmp_path / "001_second.sql").write_text("SELECT 2;\n")

    with pytest.raises(RuntimeError, match="versions must be unique"):
        discover_migrations(tmp_path)


@pytest.mark.parametrize(
    ("present", "expected"),
    [
        ([False] * 11, "empty"),
        ([True] * 11, "complete"),
        ([True] + [False] * 10, "partial"),
    ],
)
def test_detects_legacy_schema_state(present: list[bool], expected: str) -> None:
    assert _legacy_schema_state(_Cursor(present)) == expected
