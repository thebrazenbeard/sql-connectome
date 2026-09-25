from __future__ import annotations

from typing import Any

from sqlglot import exp
from sqlglot.errors import OptimizeError
from sqlglot.optimizer.annotate_types import annotate_types
from sqlglot.optimizer.qualify import qualify

from sql_connectome.receipts import canonical_digest

from .catalog import DEFAULT_CATALOG, ConnectomeCatalog
from .text_pipeline import (
    SQLTextError,
    _bounded_text,
    _parse_single_expression,
    parse_sql_text,
)


def _adapter_for(
    dialect: str,
    *,
    connectome_catalog: ConnectomeCatalog = DEFAULT_CATALOG,
) -> tuple[str, str]:
    try:
        genome = connectome_catalog.resolve(dialect)
        adapter = connectome_catalog.parser_adapter(genome.dialect_id)
    except KeyError as exc:
        raise SQLTextError(str(exc).strip("'")) from exc
    return genome.dialect_id, adapter


def _type_name(expression: exp.Expression) -> str:
    data_type = expression.type
    if data_type is None:
        return "UNKNOWN"
    return data_type.sql() if hasattr(data_type, "sql") else str(data_type)


def bind_sql_text(
    sql: str,
    dialect: str,
    schema: dict[str, dict[str, str]],
    *,
    database: str | None = None,
    catalog: str | None = None,
    connectome_catalog: ConnectomeCatalog = DEFAULT_CATALOG,
) -> dict[str, object]:
    text = _bounded_text(sql)
    if not schema:
        raise SQLTextError("EMPTY_SCHEMA_CONTEXT")

    dialect_id, adapter = _adapter_for(
        dialect,
        connectome_catalog=connectome_catalog,
    )
    source_analysis = parse_sql_text(
        text,
        dialect_id,
        catalog=connectome_catalog,
    )

    if "relational_select" not in source_analysis.ir.required_capabilities:
        raise SQLTextError("BINDING_ONLY_RELATIONAL_QUERY_SUPPORTED")

    expression = _parse_single_expression(text, adapter)
    try:
        qualified = qualify(
            expression,
            dialect=adapter,
            db=database,
            catalog=catalog,
            schema=schema,
            quote_identifiers=True,
            identify=True,
            validate_qualify_columns=True,
            sql=text,
        )
        typed = annotate_types(
            qualified,
            schema=schema,
            dialect=adapter,
        )
    except OptimizeError as exc:
        raise SQLTextError(f"STATIC_BIND_ERROR:{exc}") from exc

    columns: list[dict[str, Any]] = []
    unknown_type_count = 0

    for column in typed.find_all(exp.Column):
        type_name = _type_name(column)
        unknown = type_name.upper() == "UNKNOWN"
        if unknown:
            unknown_type_count += 1

        columns.append(
            {
                "sql": column.sql(dialect=adapter),
                "table": column.table or None,
                "name": column.name,
                "type": type_name,
                "unknown_type": unknown,
            }
        )

    projections: list[dict[str, Any]] = []
    select = next(typed.find_all(exp.Select), None)
    if select is not None:
        for projection in select.expressions:
            type_name = _type_name(projection)
            projections.append(
                {
                    "name": projection.alias_or_name or projection.sql(dialect=adapter),
                    "sql": projection.sql(dialect=adapter),
                    "type": type_name,
                    "unknown_type": type_name.upper() == "UNKNOWN",
                }
            )

    return {
        "schema": "SQL_CONNECTOME_STATIC_BINDING_V1",
        "dialect": dialect_id,
        "schema_digest": canonical_digest(schema),
        "qualified_sql": typed.sql(dialect=adapter),
        "columns": columns,
        "projections": projections,
        "binding": {
            "status": "STATIC_BOUND",
            "type_annotation": "PARTIAL" if unknown_type_count else "ANNOTATED",
            "unknown_type_count": unknown_type_count,
            "engine_validation": "NOT_RUN",
            "behavioral_equivalence": "NOT_ESTABLISHED",
            "authority": "STATIC_ANALYSIS_ONLY",
        },
        "source": source_analysis.as_dict(),
    }
