from __future__ import annotations

from typing import Any

import duckdb
from sqlglot import exp
from sqlglot.errors import ParseError

from .receipts import canonical_digest, make_receipt
from .sql_guard import validate_readonly_sql


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _normalize_type(type_name: str) -> str:
    raw = type_name.strip()
    if not raw or any(marker in raw for marker in (";", "--", "/*", "*/", "\x00")):
        raise ValueError(f"INVALID_DUCKDB_TYPE:{type_name}")

    try:
        data_type = exp.DataType.build(raw, dialect="duckdb")
    except (ParseError, ValueError, TypeError) as exc:
        raise ValueError(f"INVALID_DUCKDB_TYPE:{type_name}") from exc

    rendered = data_type.sql(dialect="duckdb")
    if any(marker in rendered for marker in (";", "--", "/*", "*/", "\x00")):
        raise ValueError(f"INVALID_DUCKDB_TYPE:{type_name}")
    return rendered


def _install_schema(
    conn: duckdb.DuckDBPyConnection,
    schema_context: dict[str, dict[str, str]],
) -> None:
    for table_name, columns in sorted(schema_context.items()):
        if not columns:
            raise ValueError(f"EMPTY_TABLE_SCHEMA:{table_name}")

        definitions = ", ".join(
            f"{_quote_identifier(column_name)} {_normalize_type(type_name)}"
            for column_name, type_name in sorted(columns.items())
        )
        try:
            conn.execute(
                f"CREATE TABLE {_quote_identifier(table_name)} ({definitions})"
            )
        except duckdb.Error as exc:
            raise ValueError(f"INVALID_DUCKDB_SCHEMA:{table_name}") from exc


def _runtime_identity(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT version() AS version,
               current_setting('enable_external_access') AS enable_external_access,
               current_setting('allow_community_extensions') AS allow_community_extensions,
               current_setting('allow_unsigned_extensions') AS allow_unsigned_extensions,
               current_setting('autoinstall_known_extensions') AS autoinstall_known_extensions,
               current_setting('autoload_known_extensions') AS autoload_known_extensions,
               current_setting('lock_configuration') AS lock_configuration,
               current_setting('threads') AS threads,
               current_setting('memory_limit') AS memory_limit
        """
    ).fetchone()
    assert row is not None

    subject = {
        "engine": "duckdb",
        "version": row[0],
        "database": ":memory:",
        "enable_external_access": row[1],
        "allow_community_extensions": row[2],
        "allow_unsigned_extensions": row[3],
        "autoinstall_known_extensions": row[4],
        "autoload_known_extensions": row[5],
        "lock_configuration": row[6],
        "threads": row[7],
        "memory_limit": row[8],
    }
    return {**subject, "identity_digest": canonical_digest(subject)}


def validate_duckdb_readonly(
    sql: str,
    *,
    schema_context: dict[str, dict[str, str]] | None = None,
    params: list[Any] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    statement = validate_readonly_sql(sql)
    schema = schema_context or {}

    config = {
        "enable_external_access": "false",
        "allow_unsigned_extensions": "false",
        "allow_community_extensions": "false",
        "autoinstall_known_extensions": "false",
        "autoload_known_extensions": "false",
        "threads": "1",
        "memory_limit": "256MB",
    }

    plan: list[list[Any]] | None = None
    error: dict[str, Any] | None = None

    with duckdb.connect(database=":memory:", config=config) as conn:
        _install_schema(conn, schema)
        conn.execute("SET lock_configuration = true")
        identity = _runtime_identity(conn)

        try:
            cursor = conn.execute(f"EXPLAIN {statement}", params or ())
            rows = cursor.fetchall()
            plan = [list(row) for row in rows]
            status = "PASS"
        except duckdb.Error as exc:
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
        "schema": "SQL_CONNECTOME_DUCKDB_ENGINE_VALIDATION_V1",
        "runtime": identity,
        "schema_context_digest": canonical_digest(schema),
        "validation": {
            "status": status,
            "engine": "duckdb",
            "mode": "EXPLAIN",
            "query_executed": False,
            "in_memory": True,
            "external_access": False,
            "behavioral_equivalence": "NOT_ESTABLISHED",
        },
        "plan": plan,
        "error": error,
        "receipt": make_receipt("DUCKDB_ENGINE_VALIDATION", subject),
    }
