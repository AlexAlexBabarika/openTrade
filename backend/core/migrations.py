"""Ordered, transactional PostgreSQL schema migrations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from backend.core.database import connection


_MIGRATION_RE = re.compile(r"^(?P<version>[0-9]+)_(?P<name>[a-z0-9_]+)\.sql$")
_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "database" / "migrations"
_LOCK_ID = 6_704_133_991
_LEGACY_TABLES = (
    "users",
    "profiles",
    "refresh_sessions",
    "api_keys",
    "api_key_audit_log",
    "exchanges",
    "symbols",
    "ticker_workspaces",
    "user_scripts",
    "user_strategies",
    "symbol_comparisons",
)


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    sql: str
    checksum: str


def discover_migrations(directory: Path = _MIGRATIONS_DIR) -> list[Migration]:
    """Load migrations in version order and reject ambiguous filenames."""
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_RE.fullmatch(path.name)
        if not match:
            raise RuntimeError(f"Invalid migration filename: {path.name}")
        payload = path.read_bytes()
        migrations.append(
            Migration(
                version=int(match.group("version")),
                name=match.group("name"),
                path=path,
                sql=payload.decode("utf-8"),
                checksum=hashlib.sha256(payload).hexdigest(),
            )
        )
    if not migrations:
        raise RuntimeError(f"No database migrations found in {directory}")
    versions = [migration.version for migration in migrations]
    if len(versions) != len(set(versions)):
        raise RuntimeError("Database migration versions must be unique")
    return sorted(migrations, key=lambda migration: migration.version)


def _legacy_schema_state(cursor) -> str:
    cursor.execute(
        "SELECT ARRAY["
        + ", ".join(
            f"to_regclass('public.{table}') IS NOT NULL" for table in _LEGACY_TABLES
        )
        + "] AS present"
    )
    present = tuple(cursor.fetchone()["present"])
    if all(present):
        return "complete"
    if any(present):
        return "partial"
    return "empty"


def apply_migrations(directory: Path = _MIGRATIONS_DIR) -> list[int]:
    """Apply pending migrations atomically and return their versions.

    Databases created by the former ``docker-entrypoint-initdb.d`` script are
    recorded as migration 1 after the complete legacy table set is verified.
    """
    migrations = discover_migrations(directory)
    applied_now: list[int] = []
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_ID,))
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version bigint PRIMARY KEY,
                name text NOT NULL,
                checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute("SELECT version, checksum FROM schema_migrations")
        applied = {
            int(row["version"]): str(row["checksum"]) for row in cursor.fetchall()
        }

        if not applied and migrations[0].version == 1:
            legacy_state = _legacy_schema_state(cursor)
            if legacy_state == "partial":
                raise RuntimeError(
                    "Database contains a partial legacy schema; restore a backup "
                    "or complete the schema before upgrading"
                )
            if legacy_state == "complete":
                baseline = migrations[0]
                cursor.execute(
                    "INSERT INTO schema_migrations (version, name, checksum) "
                    "VALUES (%s, %s, %s)",
                    (baseline.version, baseline.name, baseline.checksum),
                )
                applied[baseline.version] = baseline.checksum

        known_versions = {migration.version for migration in migrations}
        unknown = sorted(set(applied) - known_versions)
        if unknown:
            raise RuntimeError(f"Database has unknown migration versions: {unknown}")

        for migration in migrations:
            existing_checksum = applied.get(migration.version)
            if existing_checksum:
                if existing_checksum != migration.checksum:
                    raise RuntimeError(
                        f"Migration {migration.path.name} changed after it was applied"
                    )
                continue
            cursor.execute(migration.sql)
            cursor.execute(
                "INSERT INTO schema_migrations (version, name, checksum) "
                "VALUES (%s, %s, %s)",
                (migration.version, migration.name, migration.checksum),
            )
            applied_now.append(migration.version)
    return applied_now
