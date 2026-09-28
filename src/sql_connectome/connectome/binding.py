from __future__ import annotations

from typing import Any

from sqlglot import exp
from sqlglot.errors import OptimizeError
from sqlglot.optimizer.annotate_types import annotate_types
from sqlglot.optimizer.qualify import qualify

from sql_connectome.receipts import canonical_digest

from .catalog import DEFAULT_CATALOG, ConnectomeCatalog
from .ir import SQLSemanticIR
from .logical_builder import build_logical_plan
from .logical_plan import logical_plan_digest
from .text_pipeline import (
    SQLTextAnalysis,
    SQLTextError,
    _bounded_text,
    _expression_graph,
    _input_relations,
    _ir_as_dict,
    _output_fields,
    _parse_single_expression,
    parse_sql_text,
)
from .type_system import canonical_type_family


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


def _binding_node_attributes(node: exp.Expression) -> list[tuple[str, Any]]:
    type_name = _type_name(node)
    unknown = type_name.upper() == "UNKNOWN"
    family = None if unknown else canonical_type_family(type_name).value

    attributes: list[tuple[str, Any]] = [
        ("binding_type_state", "UNKNOWN" if unknown else "ANNOTATED"),
        ("binding_type_sql", type_name),
        ("binding_type_canonical_family", family),
        ("binding_type_evidence_basis", "SQLGLOT_STATIC_SCHEMA_ANNOTATION"),
    ]

    if isinstance(node, exp.Column):
        attributes.extend(
            [
                ("binding_column_name", node.name),
                ("binding_table_name", node.table or None),
            ]
        )

    return attributes


def _build_bound_ir(
    typed: exp.Expression,
    *,
    source_analysis: SQLTextAnalysis,
    dialect_id: str,
    adapter: str,
    schema_digest: str,
    type_annotation: str,
) -> tuple[dict[str, object], str, str]:
    source_ir_payload = source_analysis.as_dict()["ir"]
    source_ir_digest = canonical_digest(source_ir_payload)

    roots, nodes, edges = _expression_graph(
        typed,
        parser_dialect=adapter,
        extra_attribute_provider=_binding_node_attributes,
    )
    bound_ir = SQLSemanticIR(
        operation=typed.key.upper(),
        source_dialect=dialect_id,
        source_version=source_analysis.ir.source_version,
        roots=roots,
        nodes=nodes,
        edges=edges,
        semantic_dimensions=source_analysis.ir.semantic_dimensions,
        required_capabilities=source_analysis.ir.required_capabilities,
        input_relations=_input_relations(typed),
        output_fields=_output_fields(typed),
        type_constraints=source_analysis.ir.type_constraints,
        side_effects=source_analysis.ir.side_effects,
        semantic_extensions=source_analysis.ir.semantic_extensions
        + (
            ("binding_schema", "SQL_CONNECTOME_BOUND_SEMANTICS_V1"),
            ("binding_schema_digest", schema_digest),
            ("binding_source_ir_digest", source_ir_digest),
            ("binding_state", "STATIC_BOUND"),
            ("binding_type_annotation", type_annotation),
        ),
        provenance=source_analysis.ir.provenance
        + (
            f"schema-context:{schema_digest}",
            f"source-ir:{source_ir_digest}",
            f"static-binding:sqlglot:{source_analysis.parser_version}",
        ),
        translation_loss=source_analysis.ir.translation_loss,
    )
    bound_ir.validate_graph()
    bound_ir_payload = _ir_as_dict(bound_ir)
    bound_ir_digest = canonical_digest(bound_ir_payload)
    return bound_ir_payload, source_ir_digest, bound_ir_digest


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
    unknown_column_type_count = 0

    for column in typed.find_all(exp.Column):
        type_name = _type_name(column)
        unknown = type_name.upper() == "UNKNOWN"
        if unknown:
            unknown_column_type_count += 1

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
    unknown_projection_type_count = 0
    select = next(typed.find_all(exp.Select), None)
    if select is not None:
        for projection in select.expressions:
            type_name = _type_name(projection)
            projection_unknown = type_name.upper() == "UNKNOWN"
            if projection_unknown:
                unknown_projection_type_count += 1
            projections.append(
                {
                    "name": projection.alias_or_name or projection.sql(dialect=adapter),
                    "sql": projection.sql(dialect=adapter),
                    "type": type_name,
                    "unknown_type": projection_unknown,
                }
            )

    unknown_binding_type_count = (
        unknown_column_type_count + unknown_projection_type_count
    )
    type_annotation = (
        "PARTIAL" if unknown_binding_type_count else "ANNOTATED"
    )
    schema_digest = canonical_digest(schema)
    bound_ir_payload, source_ir_digest, bound_ir_digest = _build_bound_ir(
        typed,
        source_analysis=source_analysis,
        dialect_id=dialect_id,
        adapter=adapter,
        schema_digest=schema_digest,
        type_annotation=type_annotation,
    )

    logical_plan = build_logical_plan(
        typed,
        dialect_id=dialect_id,
        source_ir_digest=source_ir_digest,
        bound_ir_digest=bound_ir_digest,
        schema_digest=schema_digest,
    )
    logical_payload = logical_plan.as_dict()

    return {
        "schema": "SQL_CONNECTOME_STATIC_BINDING_V1",
        "catalog_digest": connectome_catalog.digest,
        "dialect": dialect_id,
        "schema_digest": schema_digest,
        "qualified_sql": typed.sql(dialect=adapter),
        "columns": columns,
        "projections": projections,
        "binding": {
            "status": "STATIC_BOUND",
            "type_annotation": type_annotation,
            "type_annotation_scope": "COLUMNS_AND_PROJECTIONS",
            "unknown_type_count": unknown_column_type_count,
            "unknown_column_type_count": unknown_column_type_count,
            "unknown_projection_type_count": unknown_projection_type_count,
            "unknown_binding_type_count": unknown_binding_type_count,
            "source_ir_digest": source_ir_digest,
            "bound_ir_digest": bound_ir_digest,
            "engine_validation": "NOT_RUN",
            "behavioral_equivalence": "NOT_ESTABLISHED",
            "authority": "STATIC_ANALYSIS_ONLY",
        },
        "bound_semantics": {
            "schema": "SQL_CONNECTOME_BOUND_SEMANTICS_V1",
            "schema_digest": schema_digest,
            "source_ir_digest": source_ir_digest,
            "bound_ir_digest": bound_ir_digest,
            "coverage": "QUALIFIED_IDENTIFIERS_AND_STATIC_TYPES",
            "engine_validation": "NOT_RUN",
            "behavioral_equivalence": "NOT_ESTABLISHED",
            "authority": "STATIC_ANALYSIS_ONLY",
            "ir": bound_ir_payload,
        },
        "logical_semantics": {
            "schema": "SQL_CONNECTOME_LOGICAL_SEMANTICS_V1",
            "plan_digest": logical_plan_digest(logical_plan),
            "source_ir_digest": source_ir_digest,
            "bound_ir_digest": bound_ir_digest,
            "schema_digest": schema_digest,
            "coverage": "RELATIONAL_SELECT_V1",
            "authority": "STATIC_ANALYSIS_ONLY",
            "engine_validation": "NOT_RUN",
            "behavioral_equivalence": "NOT_ESTABLISHED",
            "plan": logical_payload,
        },
        "source": source_analysis.as_dict(),
    }
