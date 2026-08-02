"""Direct PostgreSQL access used by the API and maintenance scripts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://opentrade:opentrade@127.0.0.1:5432/opentrade"
).strip()


class DatabaseError(Exception):
    """Stable database exception shape consumed by the HTTP error handlers."""

    def __init__(self, exc: Exception | dict[str, Any]):
        if isinstance(exc, dict):
            self.code = exc.get("code")
            self.message = str(exc.get("message", "Database error"))
            self.hint = exc.get("hint")
            self.details = exc.get("details")
        else:
            self.code = getattr(exc, "sqlstate", None)
            self.message = str(exc)
            self.hint = getattr(getattr(exc, "diag", None), "message_hint", None)
            self.details = getattr(getattr(exc, "diag", None), "message_detail", None)
        super().__init__(self.message)


@dataclass
class QueryResponse:
    data: list[dict[str, Any]] | dict[str, Any] | None


def connection():
    """Open a transaction-scoped PostgreSQL connection."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def check_database() -> None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")


class Database:
    def from_(self, table: str) -> "Query":
        return Query(table)

    table = from_


class Query:
    """Small parameterized query builder for the CRUD shapes used by OpenTrade."""

    def __init__(self, table: str):
        self.table = table
        self.operation = "select"
        self.columns = "*"
        self.payload: dict[str, Any] | list[dict[str, Any]] | None = None
        self.filters: list[tuple[str, str, Any]] = []
        self.orders: list[tuple[str, bool]] = []
        self.row_limit: int | None = None
        self.conflict_columns: list[str] = []
        self.single = False

    def select(self, columns: str = "*") -> "Query":
        self.columns = columns
        return self

    def insert(self, payload: dict | list[dict]) -> "Query":
        self.operation, self.payload = "insert", payload
        return self

    def update(self, payload: dict) -> "Query":
        self.operation, self.payload = "update", payload
        return self

    def delete(self) -> "Query":
        self.operation = "delete"
        return self

    def upsert(self, payload: dict | list[dict], on_conflict: str) -> "Query":
        self.operation, self.payload = "upsert", payload
        self.conflict_columns = [part.strip() for part in on_conflict.split(",")]
        return self

    def eq(self, column: str, value: Any) -> "Query":
        self.filters.append((column, "=", value))
        return self

    def ilike(self, column: str, value: str) -> "Query":
        self.filters.append((column, "ILIKE", value))
        return self

    def in_(self, column: str, values: list[Any]) -> "Query":
        self.filters.append((column, "IN", values))
        return self

    def order(self, column: str, desc: bool = False) -> "Query":
        self.orders.append((column, desc))
        return self

    def limit(self, value: int) -> "Query":
        self.row_limit = value
        return self

    def maybe_single(self) -> "Query":
        self.single = True
        self.row_limit = 1
        return self

    def _where(self) -> tuple[sql.Composed, list[Any]]:
        if not self.filters:
            return sql.SQL(""), []
        clauses, params = [], []
        for column, operator, value in self.filters:
            if operator == "IN":
                clauses.append(sql.SQL("{} = ANY(%s)").format(sql.Identifier(column)))
            else:
                clauses.append(
                    sql.SQL("{} {} %s").format(
                        sql.Identifier(column), sql.SQL(operator)
                    )
                )
            params.append(value)
        return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses), params

    def _returning(self) -> sql.Composed:
        return sql.SQL(" RETURNING *")

    def _select_columns(self) -> sql.Composed:
        # The only embedded relation is exchanges(code), used by symbol responses.
        if "exchange:exchanges(code)" in self.columns:
            raw = self.columns.replace(",exchange:exchanges(code)", "")
            cols = [
                sql.SQL("s.{} AS {}").format(
                    sql.Identifier(c.strip()), sql.Identifier(c.strip())
                )
                for c in raw.split(",")
            ]
            cols.append(sql.SQL("jsonb_build_object('code', e.code) AS exchange"))
            return sql.SQL(", ").join(cols)
        if self.columns.strip() == "*":
            return sql.SQL("*")
        names = [c.strip() for c in self.columns.split(",")]
        if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", c) for c in names):
            raise ValueError("Unsupported select expression")
        return sql.SQL(", ").join(sql.Identifier(c) for c in names)

    def _build(self) -> tuple[sql.Composed, list[Any]]:
        table = sql.Identifier(self.table)
        where, params = self._where()
        if self.operation == "select":
            alias = (
                sql.SQL(" s LEFT JOIN exchanges e ON e.id = s.exchange_id")
                if "exchange:exchanges(code)" in self.columns
                else sql.SQL("")
            )
            table_expr = table + alias
            statement = (
                sql.SQL("SELECT {} FROM ").format(self._select_columns())
                + table_expr
                + where
            )
            if self.orders:
                statement += sql.SQL(" ORDER BY ") + sql.SQL(", ").join(
                    sql.SQL("{} {}").format(
                        sql.Identifier(c), sql.SQL("DESC" if d else "ASC")
                    )
                    for c, d in self.orders
                )
            if self.row_limit is not None:
                statement += sql.SQL(" LIMIT %s")
                params.append(self.row_limit)
            return statement, params

        rows = self.payload if isinstance(self.payload, list) else [self.payload or {}]
        if not rows:
            raise ValueError("Database write payload cannot be empty")
        columns = list(rows[0])
        if self.operation in {"insert", "upsert"}:
            values = [
                [self._adapt_value(row.get(column)) for column in columns]
                for row in rows
            ]
            statement = sql.SQL("INSERT INTO {} ({}) VALUES ").format(
                table, sql.SQL(", ").join(map(sql.Identifier, columns))
            ) + sql.SQL(", ").join(
                sql.SQL("({})").format(
                    sql.SQL(", ").join(sql.Placeholder() for _ in columns)
                )
                for _ in rows
            )
            flat = [value for row in values for value in row]
            if self.operation == "upsert":
                updates = [c for c in columns if c not in self.conflict_columns]
                conflict = sql.SQL(" ON CONFLICT ({}) ").format(
                    sql.SQL(", ").join(map(sql.Identifier, self.conflict_columns))
                )
                if updates:
                    statement += (
                        conflict
                        + sql.SQL("DO UPDATE SET ")
                        + sql.SQL(", ").join(
                            sql.SQL("{} = EXCLUDED.{}").format(
                                sql.Identifier(c), sql.Identifier(c)
                            )
                            for c in updates
                        )
                    )
                else:
                    statement += conflict + sql.SQL("DO NOTHING")
            return statement + self._returning(), flat
        if self.operation == "update":
            statement = (
                sql.SQL("UPDATE {} SET ").format(table)
                + sql.SQL(", ").join(
                    sql.SQL("{} = %s").format(sql.Identifier(c)) for c in columns
                )
                + where
                + self._returning()
            )
            return statement, [self._adapt_value(rows[0][c]) for c in columns] + params
        if self.operation == "delete":
            return sql.SQL("DELETE FROM {} ").format(
                table
            ) + where + self._returning(), params
        raise ValueError(f"Unsupported operation: {self.operation}")

    @staticmethod
    def _adapt_value(value: Any) -> Any:
        return Jsonb(value) if isinstance(value, dict) else value

    def execute(self) -> QueryResponse:
        statement, params = self._build()
        try:
            with connection() as conn, conn.cursor() as cur:
                cur.execute(statement, params)
                rows = list(cur.fetchall())
            return QueryResponse(
                rows[0] if self.single and rows else (None if self.single else rows)
            )
        except psycopg.Error as exc:
            raise DatabaseError(exc) from exc


_database = Database()


def get_database() -> Database:
    return _database
