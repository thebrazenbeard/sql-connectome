from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlglot import ErrorLevel, exp
from sqlglot.dialects import Dialect
from sqlglot.errors import ParseError, UnsupportedError

from sql_connectome.receipts import canonical_digest

from .expression_registry import (
    DEFAULT_EXPRESSION_REGISTRY,
    ExpressionSemanticRegistry,
)


@dataclass(frozen=True, slots=True)
class ExpressionBindingProbe:
    semantic_id: str
    expected_expression_class: str
    sql: str
    purpose: str

    def as_dict(self) -> dict[str, str]:
        return {
            "semantic_id": self.semantic_id,
            "expected_expression_class": self.expected_expression_class,
            "sql": self.sql,
            "purpose": self.purpose,
        }


@dataclass(frozen=True, slots=True)
class ExpressionBindingProbeSet:
    probes: tuple[ExpressionBindingProbe, ...]

    def __post_init__(self) -> None:
        self._validate(DEFAULT_EXPRESSION_REGISTRY)

    def _validate(self, registry: ExpressionSemanticRegistry) -> None:
        seen: set[str] = set()

        for probe in self.probes:
            if probe.semantic_id in seen:
                raise ValueError(
                    f"EXPRESSION_BINDING_PROBE_DUPLICATE:{probe.semantic_id}"
                )
            seen.add(probe.semantic_id)

            semantic = next(
                (
                    entry
                    for entry in registry.entries.values()
                    if entry.semantic_id == probe.semantic_id
                ),
                None,
            )
            if semantic is None:
                raise ValueError(
                    "EXPRESSION_BINDING_PROBE_UNKNOWN_SEMANTIC:"
                    f"{probe.semantic_id}"
                )
            if semantic.expression_class != probe.expected_expression_class:
                raise ValueError(
                    "EXPRESSION_BINDING_PROBE_CLASS_MISMATCH:"
                    f"{probe.semantic_id}:"
                    f"{probe.expected_expression_class}:"
                    f"{semantic.expression_class}"
                )

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "SQL_CONNECTOME_EXPRESSION_BINDING_PROBE_SET_V1",
            "probes": [probe.as_dict() for probe in self.probes],
            "evidence_scope": "SOURCE_CONTROLLED_PROBES_ONLY",
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.manifest())


DEFAULT_EXPRESSION_BINDING_PROBES = ExpressionBindingProbeSet(
    probes=(
        ExpressionBindingProbe(
            "function.coalesce",
            "Coalesce",
            "SELECT COALESCE(NULL, 1)",
            "Null-control function binding.",
        ),
        ExpressionBindingProbe(
            "function.nullif",
            "Nullif",
            "SELECT NULLIF(1, 1)",
            "Conditional nullification binding.",
        ),
        ExpressionBindingProbe(
            "function.least",
            "Least",
            "SELECT LEAST(1, 2)",
            "Least/extrema function binding.",
        ),
        ExpressionBindingProbe(
            "function.greatest",
            "Greatest",
            "SELECT GREATEST(1, 2)",
            "Greatest/extrema function binding.",
        ),
        ExpressionBindingProbe(
            "function.length",
            "Length",
            "SELECT LENGTH('abc')",
            "String-length function binding.",
        ),
        ExpressionBindingProbe(
            "function.abs",
            "Abs",
            "SELECT ABS(-1)",
            "Absolute-value function binding.",
        ),
        ExpressionBindingProbe(
            "function.round",
            "Round",
            "SELECT ROUND(2.5, 0)",
            "Rounding function binding.",
        ),
        ExpressionBindingProbe(
            "function.log",
            "Log",
            "SELECT LOG(10, 100)",
            "Two-argument logarithm parser binding.",
        ),
        ExpressionBindingProbe(
            "aggregate.count",
            "Count",
            "SELECT COUNT(*)",
            "Count aggregate binding.",
        ),
        ExpressionBindingProbe(
            "aggregate.sum",
            "Sum",
            "SELECT SUM(x) FROM t",
            "Sum aggregate binding.",
        ),
        ExpressionBindingProbe(
            "aggregate.avg",
            "Avg",
            "SELECT AVG(x) FROM t",
            "Average aggregate binding.",
        ),
        ExpressionBindingProbe(
            "aggregate.min",
            "Min",
            "SELECT MIN(x) FROM t",
            "Minimum aggregate binding.",
        ),
        ExpressionBindingProbe(
            "aggregate.max",
            "Max",
            "SELECT MAX(x) FROM t",
            "Maximum aggregate binding.",
        ),
        ExpressionBindingProbe(
            "operator.add",
            "Add",
            "SELECT 1 + 2",
            "Addition operator binding.",
        ),
        ExpressionBindingProbe(
            "operator.div",
            "Div",
            "SELECT 5 / 2",
            "Division operator binding.",
        ),
        ExpressionBindingProbe(
            "operator.concat",
            "Concat",
            "SELECT CONCAT('a', 'b')",
            "Concatenation expression binding.",
        ),
        ExpressionBindingProbe(
            "operator.eq",
            "EQ",
            "SELECT 1 = 1",
            "Equality operator binding.",
        ),
        ExpressionBindingProbe(
            "operator.and",
            "And",
            "SELECT TRUE AND FALSE",
            "Boolean conjunction binding.",
        ),
        ExpressionBindingProbe(
            "operator.like",
            "Like",
            "SELECT 'abc' LIKE 'a%'",
            "Pattern-match operator binding.",
        ),
        ExpressionBindingProbe(
            "conversion.cast",
            "Cast",
            "SELECT CAST(1 AS INTEGER)",
            "Explicit type-conversion binding.",
        ),
    )
)


def _parse_one(sql: str, parser_dialect: str) -> exp.Expression:
    dialect = Dialect.get_or_raise(parser_dialect)
    tokens = dialect.tokenize(sql)
    parser = dialect.parser(error_level=ErrorLevel.RAISE)
    expressions = [
        expression
        for expression in parser.parse(tokens, sql)
        if expression is not None
    ]
    if len(expressions) != 1:
        raise ValueError("EXPRESSION_BINDING_PROBE_SINGLE_STATEMENT_REQUIRED")
    return expressions[0]


def _has_class(expression: exp.Expression, class_name: str) -> bool:
    return any(
        node.__class__.__name__ == class_name
        for node in expression.walk()
    )


def _error(stage: str, exc: Exception) -> dict[str, str]:
    return {
        "stage": stage,
        "error_class": exc.__class__.__name__,
        "message": str(exc).splitlines()[0],
    }


def _run_probe(
    probe: ExpressionBindingProbe,
    *,
    parser_dialect: str,
) -> dict[str, object]:
    try:
        expression = _parse_one(probe.sql, parser_dialect)
    except (ParseError, ValueError, TypeError) as exc:
        return {
            **probe.as_dict(),
            "state": "PARSE_FAILED",
            "rendered_sql": None,
            "error": _error("PARSE", exc),
        }

    if not _has_class(expression, probe.expected_expression_class):
        return {
            **probe.as_dict(),
            "state": "PARSED_WITHOUT_EXPECTED_CLASS",
            "rendered_sql": None,
            "error": None,
        }

    try:
        rendered = expression.sql(
            dialect=parser_dialect,
            unsupported_level=ErrorLevel.RAISE,
        )
    except (UnsupportedError, ValueError, TypeError) as exc:
        return {
            **probe.as_dict(),
            "state": "PARSE_BOUND_RENDER_FAILED",
            "rendered_sql": None,
            "error": _error("RENDER", exc),
        }

    try:
        reparsed = _parse_one(rendered, parser_dialect)
    except (ParseError, ValueError, TypeError) as exc:
        return {
            **probe.as_dict(),
            "state": "RENDER_REPARSE_FAILED",
            "rendered_sql": rendered,
            "error": _error("REPARSE", exc),
        }

    if not _has_class(reparsed, probe.expected_expression_class):
        return {
            **probe.as_dict(),
            "state": "RENDERED_WITHOUT_EXPECTED_CLASS",
            "rendered_sql": rendered,
            "error": None,
        }

    return {
        **probe.as_dict(),
        "state": "ROUNDTRIP_BOUND",
        "rendered_sql": rendered,
        "error": None,
    }


def probe_expression_dialect_bindings(
    *,
    dialect_id: str,
    parser_dialect: str,
    catalog_digest: str,
    registry: ExpressionSemanticRegistry = DEFAULT_EXPRESSION_REGISTRY,
    probe_set: ExpressionBindingProbeSet = DEFAULT_EXPRESSION_BINDING_PROBES,
) -> dict[str, object]:
    probe_set._validate(registry)
    results = [
        _run_probe(probe, parser_dialect=parser_dialect)
        for probe in probe_set.probes
    ]

    state_counts = Counter(str(result["state"]) for result in results)
    roundtrip_ids = sorted(
        str(result["semantic_id"])
        for result in results
        if result["state"] == "ROUNDTRIP_BOUND"
    )

    return {
        "schema": "SQL_CONNECTOME_EXPRESSION_DIALECT_BINDINGS_V1",
        "dialect_id": dialect_id,
        "parser_dialect": parser_dialect,
        "catalog_digest": catalog_digest,
        "semantic_registry_digest": registry.digest,
        "probe_set_digest": probe_set.digest,
        "probe_count": len(probe_set.probes),
        "state_counts": dict(sorted(state_counts.items())),
        "roundtrip_bound_semantic_ids": roundtrip_ids,
        "results": results,
        "evidence_basis": "SQLGLOT_PARSER_GENERATOR_PROBES",
        "evidence_scope": "SOURCE_CONTROLLED_PROBES_ONLY",
        "evidence_ceiling": "DEPENDENCY_BEHAVIOR",
        "generalization": "NOT_ESTABLISHED",
        "behavioral_equivalence": "NOT_ESTABLISHED",
    }
