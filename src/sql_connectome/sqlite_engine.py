from __future__ import annotations

import sqlite3
from typing import Any

from sqlglot import exp
from sqlglot.errors import ParseError

from .receipts import canonical_digest, make_receipt
from .sql_guard import validate_readonly_sql

MAX_SCHEMA_TABLES = 256
MAX_COLUMNS_PER_TABLE = 1024
MAX_IDENTIFIER_LENGTH = 256
MAX_TYPE_LENGTH = 256


def _quote_identifier(value: str) -> str:
    if not value or len(value) > MAX_IDENTIFIER_LENGTH or "\x00" in value:
        raise ValueError(f"INVALID_SQLITE_IDENTIFIER:{value}")
    return '"' + value.replace('"', '""') + '"'


def _normalize_type(type_name: str) -> str:
    raw = type_name.strip()
    if (
        not raw
        or len(raw) > MAX_TYPE_LENGTH
        or any(marker in raw for marker in (";", "--", "/*", "*/", "\x00"))
    ):
        raise ValueError(f"INVALID_SQLITE_TYPE:{type_name}")

    try:
        data_type = exp.DataType.build(raw, dialect="sqlite")
    except (ParseError, ValueError, TypeError) as exc:
        raise ValueError(f"INVALID_SQLITE_TYPE:{type_name}") from exc

    rendered = data_type.sql(dialect="sqlite")
    if any(marker in rendered for marker in (";", "--", "/*", "*/", "\x00")):
        raise ValueError(f"INVALID_SQLITE_TYPE:{type_name}")
    return rendered


def _install_schema(
    conn: sqlite3.Connection,
    schema_context: dict[str, dict[str, str]],
) -> None:
    if len(schema_context) > MAX_SCHEMA_TABLES:
        raise ValueError("SQLITE_SCHEMA_TABLE_LIMIT_EXCEEDED")

    for table_name, columns in sorted(schema_context.items()):
        if not columns:
            raise ValueError(f"EMPTY_TABLE_SCHEMA:{table_name}")
        if len(columns) > MAX_COLUMNS_PER_TABLE:
            raise ValueError(f"SQLITE_SCHEMA_COLUMN_LIMIT_EXCEEDED:{table_name}")

        definitions = ", ".join(
            f"{_quote_identifier(column_name)} {_normalize_type(type_name)}"
            for column_name, type_name in sorted(columns.items())
        )
        try:
            conn.execute(
                f"CREATE TABLE {_quote_identifier(table_name)} ({definitions})"
            )
        except sqlite3.Error as exc:
            raise ValueError(f"INVALID_SQLITE_SCHEMA:{table_name}") from exc


def _set_limits(conn: sqlite3.Connection) -> dict[str, int]:
    requested = {
        "sql_length": ("SQLITE_LIMIT_SQL_LENGTH", 50_000),
        "column": ("SQLITE_LIMIT_COLUMN", 2_000),
        "compound_select": ("SQLITE_LIMIT_COMPOUND_SELECT", 100),
        "expr_depth": ("SQLITE_LIMIT_EXPR_DEPTH", 1_000),
        "variable_number": ("SQLITE_LIMIT_VARIABLE_NUMBER", 1_000),
        "vdbe_op": ("SQLITE_LIMIT_VDBE_OP", 100_000),
    }

    applied: dict[str, int] = {}
    for name, (constant_name, value) in requested.items():
        constant = getattr(sqlite3, constant_name, None)
        if constant is None:
            continue
        conn.setlimit(constant, value)
        applied[name] = conn.getlimit(constant)
    return applied


def _select_authorizer(action: int, _arg1: str | None, _arg2: str | None, _db: str | None, _trigger: str | None) -> int:
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
    }
    recursive = getattr(sqlite3, "SQLITE_RECURSIVE", None)
    if recursive is not None:
        allowed.add(recursive)
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


def _runtime_identity(
    conn: sqlite3.Connection,
    limits: dict[str, int],
) -> dict[str, Any]:
    query_only = bool(conn.execute("PRAGMA query_only").fetchone()[0])
    subject = {
        "engine": "sqlite",
        "version": sqlite3.sqlite_version,
        "python_sqlite_version": sqlite3.version,
        "database": ":memory:",
        "query_only": query_only,
        "extension_loading": False,
        "authorizer": "SELECT_READ_FUNCTION_ONLY",
        "limits": limits,
    }
    return {**subject, "identity_digest": canonical_digest(subject)}


def validate_sqlite_readonly(
    sql: str,
    *,
    schema_context: dict[str, dict[str, str]] | None = None,
    params: list[Any] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    statement = validate_readonly_sql(sql)
    schema = schema_context or {}

    plan: list[list[Any]] | None = None
    error: dict[str, Any] | None = None

    with sqlite3.connect(":memory:") as conn:
        conn.enable_load_extension(False)
        limits = _set_limits(conn)
        _install_schema(conn, schema)
        conn.execute("PRAGMA trusted_schema = OFF")
        conn.execute("PRAGMA query_only = ON")
        identity = _runtime_identity(conn, limits)
        conn.set_authorizer(_select_authorizer)

        try:
            cursor = conn.execute(f"EXPLAIN QUERY PLAN {statement}", params or ())
            plan = [list(row) for row in cursor.fetchall()]
            status = "PASS"
        except sqlite3.Error as exc:
            status = "FAIL"
            error = {
                "error_class": exc.__class__.__name__,
                "message": str(exc).splitlines()[0],
            }

    subject = {
        "runtime_identity_digest": identity["identity_digest"],
        "sql_digest": canonical_digest(statement),
        "schema_digest": canonical_digest(schema),
        "status": status,
        "error_class": error["error_class"] if error else None,
    }

    return {
        "schema": "SQL_CONNECTOME_SQLITE_ENGINE_VALIDATION_V1",
        "runtime": identity,
        "schema_context_digest": canonical_digest(schema),
        "validation": {
            "status": status,
            "engine": "sqlite",
            "mode": "EXPLAIN_QUERY_PLAN",
            "query_executed": False,
            "in_memory": True,
            "extension_loading": False,
            "behavioral_equivalence": "NOT_ESTABLISHED",
        },
        "plan": plan,
        "error": error,
        "receipt": make_receipt("SQLITE_ENGINE_VALIDATION", subject),
    }
