from __future__ import annotations

import json
from typing import Any

from .engine_validation import (
    EngineRuntimeIdentity,
    NativeEngineError,
    ValidationStatus,
    build_engine_validation_result,
)
from .sql_guard import validate_readonly_sql


def _native_error(exc: Exception) -> NativeEngineError:
    fields = []
    for name in ("errno", "sqlstate"):
        value = getattr(exc, name, None)
        if value is not None:
            fields.append((name, str(value)))
    return NativeEngineError(type(exc).__name__, str(exc), tuple(fields))


def validate_mariadb_readonly(
    sql: str,
    *,
    connection: Any,
    schema_context: Any = None,
):
    validate_readonly_sql(sql)
    if connection is None:
        return build_engine_validation_result(
            runtime=EngineRuntimeIdentity("mariadb", "mariadb-v1"),
            sql=sql,
            schema_context=schema_context,
            status=ValidationStatus.UNAVAILABLE,
            validation_mode="EXPLAIN_FORMAT_JSON",
        )
    try:
        cursor = connection.cursor()
    except Exception as exc:
        return build_engine_validation_result(
            runtime=EngineRuntimeIdentity("mariadb", "mariadb-v1"),
            sql=sql,
            schema_context=schema_context,
            status=ValidationStatus.UNAVAILABLE,
            validation_mode="EXPLAIN_FORMAT_JSON",
            native_error=_native_error(exc),
        )
    try:
        cursor.execute(
            "SELECT VERSION(), DATABASE(), @@SESSION.sql_mode, "
            "@@SESSION.collation_connection, @@SESSION.time_zone, "
            "@@SESSION.character_set_connection"
        )
        row = cursor.fetchone()
        version, database, sql_mode, collation, timezone, character_set = row
        runtime = EngineRuntimeIdentity(
            "mariadb",
            "mariadb-v1",
            str(version),
            (
                ("database", str(database)),
                ("sql_mode", str(sql_mode)),
                ("collation_connection", str(collation)),
                ("time_zone", str(timezone)),
                ("character_set_connection", str(character_set)),
            ),
        )
        cursor.execute(f"EXPLAIN FORMAT=JSON {sql}")
        payload = cursor.fetchone()[0]
        try:
            payload = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            pass
        return build_engine_validation_result(
            runtime=runtime,
            sql=sql,
            schema_context=schema_context,
            status=ValidationStatus.PASS,
            validation_mode="EXPLAIN_FORMAT_JSON",
            native_payload=payload,
        )
    except Exception as exc:
        runtime = locals().get("runtime", EngineRuntimeIdentity("mariadb", "mariadb-v1"))
        return build_engine_validation_result(
            runtime=runtime,
            sql=sql,
            schema_context=schema_context,
            status=ValidationStatus.FAIL,
            validation_mode="EXPLAIN_FORMAT_JSON",
            native_error=_native_error(exc),
        )
