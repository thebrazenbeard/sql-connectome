from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from sqlglot import exp

from sql_connectome.receipts import canonical_digest


class ExpressionSemanticKind(StrEnum):
    FUNCTION = "FUNCTION"
    AGGREGATE = "AGGREGATE"
    OPERATOR = "OPERATOR"
    CONTROL = "CONTROL"
    CONVERSION = "CONVERSION"


@dataclass(frozen=True, slots=True)
class ExpressionSemantic:
    semantic_id: str
    expression_class: str
    kind: ExpressionSemanticKind
    family: str
    argument_roles: tuple[str, ...]
    known_risk_codes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "semantic_id": self.semantic_id,
            "expression_class": self.expression_class,
            "kind": self.kind.value,
            "family": self.family,
            "argument_roles": list(self.argument_roles),
            "known_risk_codes": list(self.known_risk_codes),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ExpressionSemanticRegistry:
    entries: Mapping[str, ExpressionSemantic]

    def __post_init__(self) -> None:
        normalized = dict(self.entries)
        object.__setattr__(self, "entries", MappingProxyType(normalized))
        self._validate()

    def _validate(self) -> None:
        seen_ids: set[str] = set()

        for expression_class, entry in self.entries.items():
            if expression_class != entry.expression_class:
                raise ValueError(
                    "EXPRESSION_REGISTRY_CLASS_MISMATCH:"
                    f"{expression_class}:{entry.expression_class}"
                )
            if not expression_class.strip():
                raise ValueError("EXPRESSION_REGISTRY_EMPTY_CLASS")

            semantic_id = entry.semantic_id
            if semantic_id != semantic_id.strip().lower():
                raise ValueError(
                    f"EXPRESSION_REGISTRY_ID_NOT_NORMALIZED:{semantic_id}"
                )
            if not semantic_id or any(
                not (char.isalnum() or char in "._-") for char in semantic_id
            ):
                raise ValueError(
                    f"EXPRESSION_REGISTRY_ID_INVALID:{semantic_id}"
                )
            if semantic_id in seen_ids:
                raise ValueError(
                    f"EXPRESSION_REGISTRY_ID_DUPLICATE:{semantic_id}"
                )
            seen_ids.add(semantic_id)

            if not entry.family.strip():
                raise ValueError(
                    f"EXPRESSION_REGISTRY_EMPTY_FAMILY:{semantic_id}"
                )

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "SQL_CONNECTOME_EXPRESSION_SEMANTIC_REGISTRY_V1",
            "entries": [
                entry.as_dict()
                for entry in sorted(
                    self.entries.values(),
                    key=lambda item: item.semantic_id,
                )
            ],
            "evidence_basis": "SOURCE_CONTROLLED_SEMANTIC_REGISTRY",
            "evidence_ceiling": "DECLARED_SEMANTIC_IDENTITY",
            "behavioral_equivalence": "NOT_ESTABLISHED",
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.manifest())

    def resolve_class(self, expression_class: str) -> ExpressionSemantic | None:
        return self.entries.get(expression_class)


def _entry(
    semantic_id: str,
    expression_class: str,
    kind: ExpressionSemanticKind,
    family: str,
    *argument_roles: str,
    risks: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> ExpressionSemantic:
    return ExpressionSemantic(
        semantic_id=semantic_id,
        expression_class=expression_class,
        kind=kind,
        family=family,
        argument_roles=argument_roles,
        known_risk_codes=risks,
        notes=notes,
    )


_DEFAULT_ENTRIES = (
    _entry(
        "function.coalesce",
        "Coalesce",
        ExpressionSemanticKind.CONTROL,
        "null_control",
        "candidates",
    ),
    _entry(
        "function.nullif",
        "Nullif",
        ExpressionSemanticKind.CONTROL,
        "null_control",
        "left",
        "right",
    ),
    _entry(
        "function.least",
        "Least",
        ExpressionSemanticKind.FUNCTION,
        "extrema",
        "candidates",
        risks=("LEAST_GREATEST_NULL_SEMANTICS",),
    ),
    _entry(
        "function.greatest",
        "Greatest",
        ExpressionSemanticKind.FUNCTION,
        "extrema",
        "candidates",
        risks=("LEAST_GREATEST_NULL_SEMANTICS",),
    ),
    _entry(
        "function.length",
        "Length",
        ExpressionSemanticKind.FUNCTION,
        "string_measurement",
        "value",
    ),
    _entry(
        "function.abs",
        "Abs",
        ExpressionSemanticKind.FUNCTION,
        "numeric",
        "value",
    ),
    _entry(
        "function.round",
        "Round",
        ExpressionSemanticKind.FUNCTION,
        "numeric",
        "value",
        "precision",
    ),
    _entry(
        "function.log",
        "Log",
        ExpressionSemanticKind.FUNCTION,
        "numeric",
        "value",
        "base",
        risks=("LOG_ARGUMENT_ORDER_SEMANTICS",),
    ),
    _entry(
        "aggregate.count",
        "Count",
        ExpressionSemanticKind.AGGREGATE,
        "aggregate",
        "value_or_star",
    ),
    _entry(
        "aggregate.sum",
        "Sum",
        ExpressionSemanticKind.AGGREGATE,
        "aggregate",
        "value",
    ),
    _entry(
        "aggregate.avg",
        "Avg",
        ExpressionSemanticKind.AGGREGATE,
        "aggregate",
        "value",
    ),
    _entry(
        "aggregate.min",
        "Min",
        ExpressionSemanticKind.AGGREGATE,
        "aggregate",
        "value",
    ),
    _entry(
        "aggregate.max",
        "Max",
        ExpressionSemanticKind.AGGREGATE,
        "aggregate",
        "value",
    ),
    _entry(
        "operator.add",
        "Add",
        ExpressionSemanticKind.OPERATOR,
        "arithmetic",
        "left",
        "right",
    ),
    _entry(
        "operator.sub",
        "Sub",
        ExpressionSemanticKind.OPERATOR,
        "arithmetic",
        "left",
        "right",
    ),
    _entry(
        "operator.mul",
        "Mul",
        ExpressionSemanticKind.OPERATOR,
        "arithmetic",
        "left",
        "right",
    ),
    _entry(
        "operator.div",
        "Div",
        ExpressionSemanticKind.OPERATOR,
        "arithmetic",
        "left",
        "right",
        risks=(
            "DIVISION_TYPE_SEMANTICS",
            "DIVISION_BY_ZERO_SEMANTICS",
        ),
    ),
    _entry(
        "operator.mod",
        "Mod",
        ExpressionSemanticKind.OPERATOR,
        "arithmetic",
        "left",
        "right",
    ),
    _entry(
        "operator.pow",
        "Pow",
        ExpressionSemanticKind.OPERATOR,
        "arithmetic",
        "left",
        "right",
    ),
    _entry(
        "operator.concat",
        "Concat",
        ExpressionSemanticKind.OPERATOR,
        "string",
        "parts",
        risks=(
            "CONCAT_NULL_SEMANTICS",
            "CONCAT_ARGUMENT_TYPE_SEMANTICS",
        ),
    ),
    _entry(
        "operator.eq",
        "EQ",
        ExpressionSemanticKind.OPERATOR,
        "comparison",
        "left",
        "right",
    ),
    _entry(
        "operator.neq",
        "NEQ",
        ExpressionSemanticKind.OPERATOR,
        "comparison",
        "left",
        "right",
    ),
    _entry(
        "operator.gt",
        "GT",
        ExpressionSemanticKind.OPERATOR,
        "comparison",
        "left",
        "right",
    ),
    _entry(
        "operator.gte",
        "GTE",
        ExpressionSemanticKind.OPERATOR,
        "comparison",
        "left",
        "right",
    ),
    _entry(
        "operator.lt",
        "LT",
        ExpressionSemanticKind.OPERATOR,
        "comparison",
        "left",
        "right",
    ),
    _entry(
        "operator.lte",
        "LTE",
        ExpressionSemanticKind.OPERATOR,
        "comparison",
        "left",
        "right",
    ),
    _entry(
        "operator.and",
        "And",
        ExpressionSemanticKind.OPERATOR,
        "boolean",
        "left",
        "right",
    ),
    _entry(
        "operator.or",
        "Or",
        ExpressionSemanticKind.OPERATOR,
        "boolean",
        "left",
        "right",
    ),
    _entry(
        "operator.not",
        "Not",
        ExpressionSemanticKind.OPERATOR,
        "boolean",
        "value",
    ),
    _entry(
        "operator.index",
        "Bracket",
        ExpressionSemanticKind.OPERATOR,
        "indexing",
        "container",
        "index",
        risks=("INDEX_OFFSET_SEMANTICS",),
    ),
    _entry(
        "operator.like",
        "Like",
        ExpressionSemanticKind.OPERATOR,
        "pattern_match",
        "value",
        "pattern",
    ),
    _entry(
        "operator.ilike",
        "ILike",
        ExpressionSemanticKind.OPERATOR,
        "pattern_match",
        "value",
        "pattern",
    ),
    _entry(
        "operator.regexp_like",
        "RegexpLike",
        ExpressionSemanticKind.OPERATOR,
        "pattern_match",
        "value",
        "pattern",
    ),
    _entry(
        "conversion.cast",
        "Cast",
        ExpressionSemanticKind.CONVERSION,
        "type_conversion",
        "value",
        "target_type",
    ),
)


DEFAULT_EXPRESSION_REGISTRY = ExpressionSemanticRegistry(
    entries={entry.expression_class: entry for entry in _DEFAULT_ENTRIES}
)


def _expression_name(node: exp.Expression) -> str:
    if isinstance(node, exp.Func):
        sql_name = getattr(node, "sql_name", None)
        if callable(sql_name):
            return str(sql_name()).upper()
    return node.__class__.__name__.upper()


def inspect_expression_semantics(
    expression: exp.Expression,
    *,
    dialect_id: str,
    parser_dialect: str,
    catalog_digest: str,
    registry: ExpressionSemanticRegistry = DEFAULT_EXPRESSION_REGISTRY,
) -> dict[str, object]:
    counts: dict[str, int] = {}
    representatives: dict[str, exp.Expression] = {}

    for node in expression.walk():
        expression_class = node.__class__.__name__
        if not (
            isinstance(node, exp.Func)
            or expression_class in registry.entries
        ):
            continue

        counts[expression_class] = counts.get(expression_class, 0) + 1
        representatives.setdefault(expression_class, node)

    bindings: list[dict[str, object]] = []
    registered_count = 0
    unregistered_count = 0

    for expression_class in sorted(counts):
        node = representatives[expression_class]
        semantic = registry.resolve_class(expression_class)

        if semantic is None:
            unregistered_count += 1
            bindings.append(
                {
                    "expression_class": expression_class,
                    "name": _expression_name(node),
                    "count": counts[expression_class],
                    "state": "UNREGISTERED",
                    "semantic_id": None,
                    "kind": None,
                    "family": None,
                    "argument_roles": [],
                    "known_risk_codes": [],
                    "representative_sql": node.sql(dialect=parser_dialect),
                }
            )
            continue

        registered_count += 1
        bindings.append(
            {
                "expression_class": expression_class,
                "name": _expression_name(node),
                "count": counts[expression_class],
                "state": "REGISTERED",
                "semantic_id": semantic.semantic_id,
                "kind": semantic.kind.value,
                "family": semantic.family,
                "argument_roles": list(semantic.argument_roles),
                "known_risk_codes": list(semantic.known_risk_codes),
                "representative_sql": node.sql(dialect=parser_dialect),
            }
        )

    return {
        "schema": "SQL_CONNECTOME_EXPRESSION_SEMANTIC_INVENTORY_V1",
        "dialect_id": dialect_id,
        "parser_dialect": parser_dialect,
        "catalog_digest": catalog_digest,
        "semantic_registry_digest": registry.digest,
        "coverage": "FUNCTIONS_AND_REGISTERED_OPERATORS",
        "registered_expression_classes": registered_count,
        "unregistered_expression_classes": unregistered_count,
        "bindings": bindings,
        "evidence_basis": "SOURCE_CONTROLLED_SEMANTIC_REGISTRY",
        "behavioral_equivalence": "NOT_ESTABLISHED",
    }
