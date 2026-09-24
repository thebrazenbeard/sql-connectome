from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import ErrorLevel, exp
from sqlglot.errors import ParseError, UnsupportedError

from .ir import IREdge, IRNode, SQLSemanticIR
from .model import SemanticDimension, TranslationFidelity
from .planner import plan_translation
from .registry import DEFAULT_DIALECTS, resolve_dialect

SQLGLOT_DIALECTS: dict[str, str] = {
    "postgresql": "postgres",
    "duckdb": "duckdb",
    "sqlite": "sqlite",
    "mysql": "mysql",
    "bigquery": "bigquery",
    "snowflake": "snowflake",
    "tsql": "tsql",
    "oracle": "oracle",
    "trino": "trino",
}

_EXPRESSION_CAPABILITIES: dict[str, str] = {
    "Select": "relational_select",
    "With": "cte",
    "Window": "window_functions",
    "Qualify": "qualify",
    "Lateral": "lateral_join",
    "Merge": "merge",
    "Returning": "returning",
    "Pivot": "pivot",
    "Array": "arrays",
    "Struct": "structs",
    "Map": "maps",
    "JSONExtract": "json",
    "JSONExtractScalar": "json",
    "JSONBExtract": "json",
}

_SIDE_EFFECT_OPERATIONS = {
    "alter",
    "command",
    "create",
    "delete",
    "drop",
    "grant",
    "insert",
    "merge",
    "revoke",
    "truncate",
    "update",
}


class SQLTextError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SQLTextAnalysis:
    ir: SQLSemanticIR
    normalized_sql: str
    parser_dialect: str
    parser_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "normalized_sql": self.normalized_sql,
            "parser": {
                "engine": "sqlglot",
                "version": self.parser_version,
                "dialect": self.parser_dialect,
            },
            "ir": _ir_as_dict(self.ir),
        }


def _dialect_adapter(dialect_id_or_alias: str) -> tuple[str, str]:
    genome = resolve_dialect(dialect_id_or_alias)
    adapter = SQLGLOT_DIALECTS.get(genome.dialect_id)
    if not adapter:
        raise SQLTextError(f"PARSER_ADAPTER_NOT_CONFIGURED:{genome.dialect_id}")
    return genome.dialect_id, adapter


def _extract_capabilities(expression: exp.Expression, source_sql: str) -> frozenset[str]:
    capabilities: set[str] = set()

    for node in expression.walk():
        class_name = node.__class__.__name__
        capability = _EXPRESSION_CAPABILITIES.get(class_name)
        if capability:
            capabilities.add(capability)

        if class_name == "With" and bool(node.args.get("recursive")):
            capabilities.add("recursive_cte")

        if class_name == "Pivot" and bool(node.args.get("unpivot")):
            capabilities.discard("pivot")
            capabilities.add("unpivot")

    upper = source_sql.upper()
    lexical_markers = (
        (r"\bSELECT\s+TOP\b", "top"),
        (r"\bCROSS\s+APPLY\b|\bOUTER\s+APPLY\b", "apply"),
        (r"\bCONNECT\s+BY\b", "connect_by"),
        (r"\bVARIANT\b", "variant"),
    )
    for pattern, capability in lexical_markers:
        if re.search(pattern, upper):
            capabilities.add(capability)

    return frozenset(capabilities)


def _semantic_dimensions(capabilities: frozenset[str]) -> frozenset[SemanticDimension]:
    dimensions: set[SemanticDimension] = {SemanticDimension.RELATIONAL}

    if capabilities & {"json", "variant", "objects"}:
        dimensions.add(SemanticDimension.DOCUMENT_JSON)
    if capabilities & {"arrays", "structs", "maps", "rows"}:
        dimensions.add(SemanticDimension.NESTED)
    if capabilities & {"window_functions", "qualify", "pivot", "unpivot"}:
        dimensions.add(SemanticDimension.ANALYTICAL)
    if capabilities & {"stored_procedures", "scripting"}:
        dimensions.add(SemanticDimension.PROCEDURAL)
    if "geospatial" in capabilities:
        dimensions.add(SemanticDimension.GEOSPATIAL)
    if "federation" in capabilities:
        dimensions.add(SemanticDimension.FEDERATED)

    return frozenset(dimensions)


def _expression_graph(expression: exp.Expression) -> tuple[
    tuple[str, ...],
    tuple[IRNode, ...],
    tuple[IREdge, ...],
]:
    nodes: list[IRNode] = []
    edges: list[IREdge] = []

    def visit(
        node: exp.Expression,
        *,
        parent_id: str | None = None,
        relation: str = "ROOT",
    ) -> str:
        node_id = f"n{len(nodes)}"
        attributes: list[tuple[str, Any]] = [("expression_key", node.key)]

        if isinstance(node, exp.Table):
            attributes.append(("name", node.name))
        elif isinstance(node, exp.Column):
            attributes.append(("name", node.name))

        nodes.append(
            IRNode(
                node_id=node_id,
                kind=node.__class__.__name__.upper(),
                attributes=tuple(attributes),
            )
        )

        if parent_id is not None:
            edges.append(IREdge(source=parent_id, target=node_id, relation=relation))

        for arg_name, value in node.args.items():
            if isinstance(value, exp.Expression):
                visit(value, parent_id=node_id, relation=arg_name.upper())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, exp.Expression):
                        visit(item, parent_id=node_id, relation=arg_name.upper())

        return node_id

    root = visit(expression)
    return (root,), tuple(nodes), tuple(edges)


def _output_fields(expression: exp.Expression) -> tuple[str, ...]:
    select = next(expression.find_all(exp.Select), None)
    if select is None:
        return ()

    values: list[str] = []
    for projection in select.expressions:
        alias = projection.alias_or_name
        values.append(alias or projection.sql())
    return tuple(values)


def _input_relations(expression: exp.Expression) -> tuple[str, ...]:
    return tuple(sorted({table.name for table in expression.find_all(exp.Table) if table.name}))


def _side_effects(expression: exp.Expression) -> frozenset[str]:
    operation = expression.key.lower()
    if operation in _SIDE_EFFECT_OPERATIONS:
        return frozenset({operation.upper()})
    return frozenset()


def _ir_as_dict(ir: SQLSemanticIR) -> dict[str, object]:
    return {
        "operation": ir.operation,
        "source_dialect": ir.source_dialect,
        "source_version": ir.source_version,
        "roots": list(ir.roots),
        "nodes": [
            {
                "node_id": node.node_id,
                "kind": node.kind,
                "attributes": dict(node.attributes),
            }
            for node in ir.nodes
        ],
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "relation": edge.relation,
                "attributes": dict(edge.attributes),
            }
            for edge in ir.edges
        ],
        "semantic_dimensions": sorted(dimension.value for dimension in ir.semantic_dimensions),
        "required_capabilities": sorted(ir.required_capabilities),
        "input_relations": list(ir.input_relations),
        "output_fields": list(ir.output_fields),
        "type_constraints": list(ir.type_constraints),
        "side_effects": sorted(ir.side_effects),
        "semantic_extensions": dict(ir.semantic_extensions),
        "provenance": list(ir.provenance),
        "translation_loss": [
            {
                "kind": loss.kind,
                "description": loss.description,
                "source_fragment": loss.source_fragment,
            }
            for loss in ir.translation_loss
        ],
    }


def parse_sql_text(sql: str, dialect: str) -> SQLTextAnalysis:
    text = sql.strip()
    if not text:
        raise SQLTextError("EMPTY_SQL")

    dialect_id, parser_dialect = _dialect_adapter(dialect)
    genome = DEFAULT_DIALECTS[dialect_id]

    try:
        parsed = [
            expression
            for expression in sqlglot.parse(
                text,
                read=parser_dialect,
                error_level=ErrorLevel.RAISE,
            )
            if expression is not None
        ]
    except ParseError as exc:
        raise SQLTextError(f"PARSE_ERROR:{exc}") from exc

    if len(parsed) != 1:
        raise SQLTextError("SINGLE_STATEMENT_REQUIRED")

    expression = parsed[0]
    capabilities = _extract_capabilities(expression, text)

    # This validates that every capability we claim to have observed is admitted
    # by the declared source dialect genome.
    try:
        plan_translation(dialect_id, dialect_id, capabilities)
    except ValueError as exc:
        raise SQLTextError(str(exc)) from exc

    roots, nodes, edges = _expression_graph(expression)
    ir = SQLSemanticIR(
        operation=expression.key.upper(),
        source_dialect=dialect_id,
        source_version=genome.version_selector,
        roots=roots,
        nodes=nodes,
        edges=edges,
        semantic_dimensions=_semantic_dimensions(capabilities),
        required_capabilities=capabilities,
        input_relations=_input_relations(expression),
        output_fields=_output_fields(expression),
        side_effects=_side_effects(expression),
        provenance=(
            f"parser:sqlglot:{sqlglot.__version__}",
            f"dialect:{dialect_id}:{genome.version_selector}",
        ),
    )
    ir.validate_graph()

    return SQLTextAnalysis(
        ir=ir,
        normalized_sql=expression.sql(dialect=parser_dialect),
        parser_dialect=parser_dialect,
        parser_version=sqlglot.__version__,
    )


def transpile_sql_text(
    sql: str,
    source_dialect: str,
    target_dialect: str,
    *,
    allow_lossy: bool = False,
) -> dict[str, object]:
    source = parse_sql_text(sql, source_dialect)
    target_id, target_adapter = _dialect_adapter(target_dialect)
    source_id, source_adapter = _dialect_adapter(source_dialect)

    plan = plan_translation(
        source_id,
        target_id,
        source.ir.required_capabilities,
    )

    if plan.fidelity is TranslationFidelity.UNREPRESENTABLE:
        unresolved = ",".join(sorted(plan.unresolved_capabilities))
        raise SQLTextError(f"UNREPRESENTABLE_TRANSLATION:{unresolved}")

    if plan.fidelity is TranslationFidelity.LOSSY and not allow_lossy:
        raise SQLTextError("LOSSY_TRANSLATION_REQUIRES_OPT_IN")

    try:
        generated = sqlglot.transpile(
            sql,
            read=source_adapter,
            write=target_adapter,
            error_level=ErrorLevel.RAISE,
            unsupported_level=ErrorLevel.RAISE,
        )
    except (ParseError, UnsupportedError) as exc:
        raise SQLTextError(f"TRANSPILER_REJECTED:{exc}") from exc

    if len(generated) != 1:
        raise SQLTextError("TRANSPILER_STATEMENT_COUNT_MISMATCH")

    target = parse_sql_text(generated[0], target_id)

    return {
        "source": source.as_dict(),
        "target_sql": generated[0],
        "target_parse": target.as_dict(),
        "plan": plan.as_dict(),
        "validation": {
            "source_parse": "PASS",
            "target_parse": "PASS",
            "behavioral_equivalence": "NOT_ESTABLISHED",
            "execution_validation": "NOT_RUN",
        },
    }
