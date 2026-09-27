from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlglot import exp

from sql_connectome.receipts import canonical_digest


class OperationKind(StrEnum):
    FUNCTION = "FUNCTION"
    OPERATOR = "OPERATOR"


class EvaluationClass(StrEnum):
    SCALAR = "SCALAR"
    AGGREGATE = "AGGREGATE"
    PREDICATE = "PREDICATE"
    BOOLEAN = "BOOLEAN"
    INDEX = "INDEX"
    CONTEXT = "CONTEXT"


class DeterminismClass(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    STATEMENT_STABLE = "STATEMENT_STABLE"
    VOLATILE = "VOLATILE"
    DIALECT_DEPENDENT = "DIALECT_DEPENDENT"


OPERATOR_EXPRESSION_CLASSES = frozenset(
    {
        "Add",
        "Sub",
        "Mul",
        "Div",
        "Mod",
        "Pow",
        "EQ",
        "NEQ",
        "GT",
        "GTE",
        "LT",
        "LTE",
        "And",
        "Or",
        "Not",
        "Concat",
        "Bracket",
        "Like",
        "ILike",
        "RegexpLike",
    }
)


@dataclass(frozen=True, slots=True)
class OperationSpec:
    semantic_id: str
    canonical_name: str
    kind: OperationKind
    family: str
    expression_classes: tuple[str, ...]
    evaluation_class: EvaluationClass
    determinism: DeterminismClass
    semantic_risk_codes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    authority_effect: str = "NONE"

    def as_dict(self) -> dict[str, object]:
        return {
            "semantic_id": self.semantic_id,
            "canonical_name": self.canonical_name,
            "kind": self.kind.value,
            "family": self.family,
            "expression_classes": list(self.expression_classes),
            "evaluation_class": self.evaluation_class.value,
            "determinism": self.determinism.value,
            "semantic_risk_codes": list(self.semantic_risk_codes),
            "notes": list(self.notes),
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True, slots=True)
class OperationCatalog:
    operations: tuple[OperationSpec, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "operations", tuple(self.operations))
        self._validate()

    def _validate(self) -> None:
        semantic_ids: set[str] = set()
        expression_classes: dict[str, str] = {}

        for spec in self.operations:
            if spec.semantic_id != spec.semantic_id.strip().lower():
                raise ValueError(
                    f"OPERATION_ID_NOT_NORMALIZED:{spec.semantic_id}"
                )
            if not spec.semantic_id or "." not in spec.semantic_id:
                raise ValueError(f"OPERATION_ID_INVALID:{spec.semantic_id}")
            if spec.semantic_id in semantic_ids:
                raise ValueError(f"OPERATION_ID_DUPLICATE:{spec.semantic_id}")
            semantic_ids.add(spec.semantic_id)

            if not spec.expression_classes:
                raise ValueError(
                    f"OPERATION_EXPRESSION_CLASS_REQUIRED:{spec.semantic_id}"
                )

            for class_name in spec.expression_classes:
                owner = expression_classes.get(class_name)
                if owner is not None:
                    raise ValueError(
                        f"OPERATION_EXPRESSION_CLASS_COLLISION:{class_name}:{owner}:{spec.semantic_id}"
                    )
                if not hasattr(exp, class_name):
                    raise ValueError(
                        f"OPERATION_UNKNOWN_EXPRESSION_CLASS:{spec.semantic_id}:{class_name}"
                    )
                expression_classes[class_name] = spec.semantic_id

            if spec.authority_effect != "NONE":
                raise ValueError(
                    f"OPERATION_AUTHORITY_EFFECT_NOT_ALLOWED:{spec.semantic_id}"
                )

            for risk_code in spec.semantic_risk_codes:
                if risk_code != risk_code.upper():
                    raise ValueError(
                        f"OPERATION_RISK_CODE_NOT_NORMALIZED:{spec.semantic_id}:{risk_code}"
                    )

    def resolve_expression_class(self, class_name: str) -> OperationSpec | None:
        for spec in self.operations:
            if class_name in spec.expression_classes:
                return spec
        return None

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "SQL_CONNECTOME_OPERATION_CATALOG_V1",
            "scope": "FUNCTIONS_AND_OPERATORS_ONLY",
            "operation_count": len(self.operations),
            "operations": [
                spec.as_dict()
                for spec in sorted(
                    self.operations,
                    key=lambda item: item.semantic_id,
                )
            ],
            "unmapped_meaning": "UNKNOWN_NOT_UNSUPPORTED",
            "behavioral_equivalence": "NOT_ESTABLISHED",
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.manifest())

    def admit(self, spec: OperationSpec) -> OperationCatalog:
        return OperationCatalog(operations=(*self.operations, spec))


def _spec(
    semantic_id: str,
    canonical_name: str,
    *,
    kind: OperationKind,
    family: str,
    expression_class: str,
    evaluation_class: EvaluationClass,
    determinism: DeterminismClass = DeterminismClass.DETERMINISTIC,
    risks: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> OperationSpec:
    return OperationSpec(
        semantic_id=semantic_id,
        canonical_name=canonical_name,
        kind=kind,
        family=family,
        expression_classes=(expression_class,),
        evaluation_class=evaluation_class,
        determinism=determinism,
        semantic_risk_codes=risks,
        notes=notes,
    )


DEFAULT_OPERATION_CATALOG = OperationCatalog(
    operations=(
        _spec(
            "arithmetic.add",
            "ADD",
            kind=OperationKind.OPERATOR,
            family="arithmetic",
            expression_class="Add",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "arithmetic.subtract",
            "SUBTRACT",
            kind=OperationKind.OPERATOR,
            family="arithmetic",
            expression_class="Sub",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "arithmetic.multiply",
            "MULTIPLY",
            kind=OperationKind.OPERATOR,
            family="arithmetic",
            expression_class="Mul",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "arithmetic.divide",
            "DIVIDE",
            kind=OperationKind.OPERATOR,
            family="arithmetic",
            expression_class="Div",
            evaluation_class=EvaluationClass.SCALAR,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            risks=(
                "DIVISION_TYPE_SEMANTICS",
                "DIVISION_BY_ZERO_SEMANTICS",
            ),
        ),
        _spec(
            "arithmetic.modulo",
            "MODULO",
            kind=OperationKind.OPERATOR,
            family="arithmetic",
            expression_class="Mod",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "arithmetic.power",
            "POWER",
            kind=OperationKind.OPERATOR,
            family="arithmetic",
            expression_class="Pow",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "comparison.equal",
            "EQUAL",
            kind=OperationKind.OPERATOR,
            family="comparison",
            expression_class="EQ",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "comparison.not_equal",
            "NOT_EQUAL",
            kind=OperationKind.OPERATOR,
            family="comparison",
            expression_class="NEQ",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "comparison.greater_than",
            "GREATER_THAN",
            kind=OperationKind.OPERATOR,
            family="comparison",
            expression_class="GT",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "comparison.greater_than_or_equal",
            "GREATER_THAN_OR_EQUAL",
            kind=OperationKind.OPERATOR,
            family="comparison",
            expression_class="GTE",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "comparison.less_than",
            "LESS_THAN",
            kind=OperationKind.OPERATOR,
            family="comparison",
            expression_class="LT",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "comparison.less_than_or_equal",
            "LESS_THAN_OR_EQUAL",
            kind=OperationKind.OPERATOR,
            family="comparison",
            expression_class="LTE",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "boolean.and",
            "AND",
            kind=OperationKind.OPERATOR,
            family="boolean",
            expression_class="And",
            evaluation_class=EvaluationClass.BOOLEAN,
        ),
        _spec(
            "boolean.or",
            "OR",
            kind=OperationKind.OPERATOR,
            family="boolean",
            expression_class="Or",
            evaluation_class=EvaluationClass.BOOLEAN,
        ),
        _spec(
            "boolean.not",
            "NOT",
            kind=OperationKind.OPERATOR,
            family="boolean",
            expression_class="Not",
            evaluation_class=EvaluationClass.BOOLEAN,
        ),
        _spec(
            "string.concat",
            "CONCAT",
            kind=OperationKind.OPERATOR,
            family="string",
            expression_class="Concat",
            evaluation_class=EvaluationClass.SCALAR,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            risks=(
                "CONCAT_NULL_SEMANTICS",
                "CONCAT_ARGUMENT_TYPE_SEMANTICS",
            ),
        ),
        _spec(
            "index.bracket",
            "INDEX",
            kind=OperationKind.OPERATOR,
            family="indexing",
            expression_class="Bracket",
            evaluation_class=EvaluationClass.INDEX,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            risks=("INDEX_OFFSET_SEMANTICS",),
        ),
        _spec(
            "pattern.like",
            "LIKE",
            kind=OperationKind.OPERATOR,
            family="pattern",
            expression_class="Like",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "pattern.ilike",
            "ILIKE",
            kind=OperationKind.OPERATOR,
            family="pattern",
            expression_class="ILike",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "pattern.regexp_like",
            "REGEXP_LIKE",
            kind=OperationKind.OPERATOR,
            family="pattern",
            expression_class="RegexpLike",
            evaluation_class=EvaluationClass.PREDICATE,
        ),
        _spec(
            "null.coalesce",
            "COALESCE",
            kind=OperationKind.FUNCTION,
            family="null",
            expression_class="Coalesce",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "ordering.least",
            "LEAST",
            kind=OperationKind.FUNCTION,
            family="ordering",
            expression_class="Least",
            evaluation_class=EvaluationClass.SCALAR,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            risks=("LEAST_GREATEST_NULL_SEMANTICS",),
        ),
        _spec(
            "ordering.greatest",
            "GREATEST",
            kind=OperationKind.FUNCTION,
            family="ordering",
            expression_class="Greatest",
            evaluation_class=EvaluationClass.SCALAR,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            risks=("LEAST_GREATEST_NULL_SEMANTICS",),
        ),
        _spec(
            "string.length",
            "LENGTH",
            kind=OperationKind.FUNCTION,
            family="string",
            expression_class="Length",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "numeric.abs",
            "ABS",
            kind=OperationKind.FUNCTION,
            family="numeric",
            expression_class="Abs",
            evaluation_class=EvaluationClass.SCALAR,
        ),
        _spec(
            "numeric.round",
            "ROUND",
            kind=OperationKind.FUNCTION,
            family="numeric",
            expression_class="Round",
            evaluation_class=EvaluationClass.SCALAR,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            notes=("Rounding mode may differ across engines and input types.",),
        ),
        _spec(
            "math.log",
            "LOG",
            kind=OperationKind.FUNCTION,
            family="math",
            expression_class="Log",
            evaluation_class=EvaluationClass.SCALAR,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            risks=("LOG_ARGUMENT_ORDER_SEMANTICS",),
        ),
        _spec(
            "aggregate.count",
            "COUNT",
            kind=OperationKind.FUNCTION,
            family="aggregate",
            expression_class="Count",
            evaluation_class=EvaluationClass.AGGREGATE,
        ),
        _spec(
            "aggregate.sum",
            "SUM",
            kind=OperationKind.FUNCTION,
            family="aggregate",
            expression_class="Sum",
            evaluation_class=EvaluationClass.AGGREGATE,
        ),
        _spec(
            "aggregate.avg",
            "AVG",
            kind=OperationKind.FUNCTION,
            family="aggregate",
            expression_class="Avg",
            evaluation_class=EvaluationClass.AGGREGATE,
            determinism=DeterminismClass.DIALECT_DEPENDENT,
            notes=("Accumulator and return-type semantics can vary by engine.",),
        ),
        _spec(
            "aggregate.min",
            "MIN",
            kind=OperationKind.FUNCTION,
            family="aggregate",
            expression_class="Min",
            evaluation_class=EvaluationClass.AGGREGATE,
        ),
        _spec(
            "aggregate.max",
            "MAX",
            kind=OperationKind.FUNCTION,
            family="aggregate",
            expression_class="Max",
            evaluation_class=EvaluationClass.AGGREGATE,
        ),
        _spec(
            "context.current_timestamp",
            "CURRENT_TIMESTAMP",
            kind=OperationKind.FUNCTION,
            family="context",
            expression_class="CurrentTimestamp",
            evaluation_class=EvaluationClass.CONTEXT,
            determinism=DeterminismClass.STATEMENT_STABLE,
        ),
        _spec(
            "random.rand",
            "RAND",
            kind=OperationKind.FUNCTION,
            family="random",
            expression_class="Rand",
            evaluation_class=EvaluationClass.CONTEXT,
            determinism=DeterminismClass.VOLATILE,
        ),
    )
)


def _normalized_name(node: exp.Expression) -> str:
    if isinstance(node, exp.Anonymous):
        return node.name.upper()
    if isinstance(node, exp.Func):
        sql_name = getattr(node, "sql_name", None)
        if callable(sql_name):
            return str(sql_name()).upper()
    return node.__class__.__name__.upper()


def _is_operation_candidate(node: exp.Expression) -> bool:
    return isinstance(node, exp.Func) or node.__class__.__name__ in OPERATOR_EXPRESSION_CLASSES


def operation_graph(
    expression: exp.Expression,
    *,
    dialect_id: str,
    parser_dialect: str,
    operation_catalog: OperationCatalog = DEFAULT_OPERATION_CATALOG,
) -> dict[str, object]:
    rows: dict[tuple[str, str], dict[str, object]] = {}

    for node in expression.walk():
        if not _is_operation_candidate(node):
            continue

        class_name = node.__class__.__name__
        normalized_name = _normalized_name(node)
        key = (class_name, normalized_name)
        existing = rows.get(key)
        if existing is not None:
            existing["count"] = int(existing["count"]) + 1
            continue

        spec = operation_catalog.resolve_expression_class(class_name)
        if spec is None:
            rows[key] = {
                "mapping_status": "UNMAPPED",
                "semantic_id": None,
                "normalized_name": normalized_name,
                "expression_class": class_name,
                "kind": "FUNCTION" if isinstance(node, exp.Func) else "OPERATOR",
                "family": None,
                "evaluation_class": None,
                "determinism": "UNKNOWN",
                "authority_effect": "UNKNOWN",
                "semantic_risk_codes": [],
                "count": 1,
            }
            continue

        rows[key] = {
            "mapping_status": "ADMITTED",
            "semantic_id": spec.semantic_id,
            "normalized_name": normalized_name,
            "expression_class": class_name,
            "kind": spec.kind.value,
            "family": spec.family,
            "evaluation_class": spec.evaluation_class.value,
            "determinism": spec.determinism.value,
            "authority_effect": spec.authority_effect,
            "semantic_risk_codes": list(spec.semantic_risk_codes),
            "count": 1,
        }

    operations = sorted(
        rows.values(),
        key=lambda row: (
            str(row["mapping_status"]),
            str(row["semantic_id"]),
            str(row["normalized_name"]),
            str(row["expression_class"]),
        ),
    )
    mapped_occurrences = sum(
        int(row["count"])
        for row in operations
        if row["mapping_status"] == "ADMITTED"
    )
    unmapped_occurrences = sum(
        int(row["count"])
        for row in operations
        if row["mapping_status"] == "UNMAPPED"
    )

    return {
        "schema": "SQL_CONNECTOME_OPERATION_GRAPH_V1",
        "dialect_id": dialect_id,
        "parser_dialect": parser_dialect,
        "scope": "QUERY_SCOPED_FUNCTIONS_AND_OPERATORS",
        "operation_catalog_digest": operation_catalog.digest,
        "admitted_operation_count": len(operation_catalog.operations),
        "operations": operations,
        "mapped_occurrence_count": mapped_occurrences,
        "unmapped_occurrence_count": unmapped_occurrences,
        "unmapped_meaning": "UNKNOWN_NOT_UNSUPPORTED",
        "evidence_basis": "SOURCE_CONTROLLED_OPERATION_CATALOG_AND_SQLGLOT_AST",
        "behavioral_equivalence": "NOT_ESTABLISHED",
    }
