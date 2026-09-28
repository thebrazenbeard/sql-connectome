from __future__ import annotations

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
    for name in ("error_name", "error_type", "error_code", "query_id"):
        value = getattr(exc, name, None)
        if value is not None:
            fields.append((name, str(value)))
    return NativeEngineError(type(exc).__name__, str(exc), tuple(fields))


def validate_trino_readonly(
    sql: str,
    *,
    connection: Any,
    schema_context: Any = None,
):
    validate_readonly_sql(sql)
    if connection is None:
        return build_engine_validation_result(
            runtime=EngineRuntimeIdentity("trino", "trino-v1"),
            sql=sql,
            schema_context=schema_context,
            status=ValidationStatus.UNAVAILABLE,
            validation_mode="EXPLAIN_TYPE_VALIDATE",
        )
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT version(), current_catalog, current_schema")
        version, catalog, schema = cursor.fetchone()
        runtime = EngineRuntimeIdentity(
            "trino",
            "trino-v1",
            str(version),
            (("catalog", str(catalog)), ("schema", str(schema))),
        )
        cursor.execute(f"EXPLAIN (TYPE VALIDATE) {sql}")
        payload = cursor.fetchone()
        status = ValidationStatus.PASS if payload and bool(payload[0]) else ValidationStatus.FAIL
        return build_engine_validation_result(
            runtime=runtime,
            sql=sql,
            schema_context=schema_context,
            status=status,
            validation_mode="EXPLAIN_TYPE_VALIDATE",
            native_payload=payload,
        )
    except Exception as exc:
        runtime = locals().get("runtime", EngineRuntimeIdentity("trino", "trino-v1"))
        return build_engine_validation_result(
            runtime=runtime,
            sql=sql,
            schema_context=schema_context,
            status=ValidationStatus.FAIL,
            validation_mode="EXPLAIN_TYPE_VALIDATE",
            native_error=_native_error(exc),
        )
