from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlglot import exp
from sqlglot.dialects import Dialect

from .model import TranslationFidelity


@dataclass(frozen=True, slots=True)
class SemanticRisk:
    code: str
    expression_family: str
    source_value: object
    target_value: object
    condition: str
    description: str
    fidelity: TranslationFidelity = TranslationFidelity.LOSSY

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "expression_family": self.expression_family,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "condition": self.condition,
            "description": self.description,
            "fidelity": self.fidelity.value,
        }


def _dialect_flag(parser_dialect: str, name: str) -> object:
    dialect = Dialect.get_or_raise(parser_dialect)
    return getattr(dialect, name, None)


def dialect_semantic_profile(
    dialect_id: str,
    parser_dialect: str,
) -> dict[str, object]:
    flags = {
        "null_ordering": _dialect_flag(parser_dialect, "NULL_ORDERING"),
        "typed_division": _dialect_flag(parser_dialect, "TYPED_DIVISION"),
        "safe_division": _dialect_flag(parser_dialect, "SAFE_DIVISION"),
        "concat_coalesce": _dialect_flag(parser_dialect, "CONCAT_COALESCE"),
        "concat_ws_coalesce": _dialect_flag(parser_dialect, "CONCAT_WS_COALESCE"),
        "least_greatest_ignores_nulls": _dialect_flag(
            parser_dialect,
            "LEAST_GREATEST_IGNORES_NULLS",
        ),
        "index_offset": _dialect_flag(parser_dialect, "INDEX_OFFSET"),
        "strict_string_concat": _dialect_flag(parser_dialect, "STRICT_STRING_CONCAT"),
        "supports_user_defined_types": _dialect_flag(
            parser_dialect,
            "SUPPORTS_USER_DEFINED_TYPES",
        ),
        "log_base_first": _dialect_flag(parser_dialect, "LOG_BASE_FIRST"),
    }
    return {
        "dialect_id": dialect_id,
        "parser_dialect": parser_dialect,
        "source": "SQLGLOT_DIALECT_FLAGS",
        "flags": flags,
    }


def _expression_inventory(expression: exp.Expression) -> dict[str, list[dict[str, object]]]:
    functions: dict[str, int] = {}
    operators: dict[str, int] = {}
    types: dict[str, int] = {}

    operator_classes = {
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

    for node in expression.walk():
        class_name = node.__class__.__name__

        if isinstance(node, exp.Func):
            sql_name = getattr(node, "sql_name", None)
            if callable(sql_name):
                name = str(sql_name()).upper()
            else:
                name = class_name.upper()
            functions[name] = functions.get(name, 0) + 1

        if class_name in operator_classes:
            operators[class_name.upper()] = operators.get(class_name.upper(), 0) + 1

        if isinstance(node, exp.DataType):
            name = node.sql().upper()
            types[name] = types.get(name, 0) + 1

    def rows(values: dict[str, int]) -> list[dict[str, object]]:
        return [
            {"name": name, "count": count}
            for name, count in sorted(values.items())
        ]

    return {
        "functions": rows(functions),
        "operators": rows(operators),
        "types": rows(types),
    }


def _has_class(expression: exp.Expression, class_name: str) -> bool:
    return any(node.__class__.__name__ == class_name for node in expression.walk())


def _has_any_class(expression: exp.Expression, names: set[str]) -> bool:
    return any(node.__class__.__name__ in names for node in expression.walk())


def _flag_risk(
    *,
    code: str,
    expression_family: str,
    source_profile: dict[str, object],
    target_profile: dict[str, object],
    flag: str,
    condition: str,
    description: str,
) -> SemanticRisk | None:
    source_flags = source_profile["flags"]
    target_flags = target_profile["flags"]
    assert isinstance(source_flags, dict)
    assert isinstance(target_flags, dict)

    source_value = source_flags.get(flag)
    target_value = target_flags.get(flag)

    if source_value == target_value:
        return None

    return SemanticRisk(
        code=code,
        expression_family=expression_family,
        source_value=source_value,
        target_value=target_value,
        condition=condition,
        description=description,
    )


def assess_expression_semantics(
    expression: exp.Expression,
    *,
    source_dialect: str,
    target_dialect: str,
    source_parser_dialect: str,
    target_parser_dialect: str,
) -> dict[str, object]:
    source_profile = dialect_semantic_profile(source_dialect, source_parser_dialect)
    target_profile = dialect_semantic_profile(target_dialect, target_parser_dialect)
    risks: list[SemanticRisk] = []

    if _has_any_class(expression, {"Least", "Greatest"}):
        risk = _flag_risk(
            code="LEAST_GREATEST_NULL_SEMANTICS",
            expression_family="LEAST_GREATEST",
            source_profile=source_profile,
            target_profile=target_profile,
            flag="least_greatest_ignores_nulls",
            condition="At least one argument evaluates to NULL.",
            description=(
                "Source and target dialects disagree on whether LEAST/GREATEST "
                "ignore NULL arguments."
            ),
        )
        if risk:
            risks.append(risk)

    if _has_class(expression, "Div"):
        for risk in (
            _flag_risk(
                code="DIVISION_TYPE_SEMANTICS",
                expression_family="DIVISION",
                source_profile=source_profile,
                target_profile=target_profile,
                flag="typed_division",
                condition="Both division operands resolve to integer-like types.",
                description=(
                    "Source and target dialects disagree on whether integer operand "
                    "types change division semantics."
                ),
            ),
            _flag_risk(
                code="DIVISION_BY_ZERO_SEMANTICS",
                expression_family="DIVISION",
                source_profile=source_profile,
                target_profile=target_profile,
                flag="safe_division",
                condition="The divisor evaluates to zero.",
                description=(
                    "Source and target dialects disagree on whether division by zero "
                    "returns NULL or raises an error."
                ),
            ),
        ):
            if risk:
                risks.append(risk)

    if _has_class(expression, "Concat"):
        for risk in (
            _flag_risk(
                code="CONCAT_NULL_SEMANTICS",
                expression_family="CONCAT",
                source_profile=source_profile,
                target_profile=target_profile,
                flag="concat_coalesce",
                condition="At least one CONCAT argument evaluates to NULL.",
                description=(
                    "Source and target dialects disagree on CONCAT NULL coalescing."
                ),
            ),
            _flag_risk(
                code="CONCAT_ARGUMENT_TYPE_SEMANTICS",
                expression_family="CONCAT",
                source_profile=source_profile,
                target_profile=target_profile,
                flag="strict_string_concat",
                condition="At least one CONCAT argument is not already a string.",
                description=(
                    "Source and target dialects disagree on whether CONCAT arguments "
                    "must already be strings."
                ),
            ),
        ):
            if risk:
                risks.append(risk)

    if _has_class(expression, "Bracket"):
        risk = _flag_risk(
            code="INDEX_OFFSET_SEMANTICS",
            expression_family="INDEXING",
            source_profile=source_profile,
            target_profile=target_profile,
            flag="index_offset",
            condition="The expression performs positional indexing.",
            description=(
                "Source and target dialects use different base offsets for positional indexing."
            ),
        )
        if risk:
            risks.append(risk)

    if _has_class(expression, "Log"):
        risk = _flag_risk(
            code="LOG_ARGUMENT_ORDER_SEMANTICS",
            expression_family="LOG",
            source_profile=source_profile,
            target_profile=target_profile,
            flag="log_base_first",
            condition="LOG is called with a base and a value.",
            description=(
                "Source and target dialects disagree on argument order for two-argument LOG."
            ),
        )
        if risk:
            risks.append(risk)

    fidelity_ceiling = (
        TranslationFidelity.LOSSY
        if risks
        else TranslationFidelity.EXACT
    )

    return {
        "schema": "SQL_CONNECTOME_EXPRESSION_SEMANTICS_V1",
        "source": source_profile,
        "target": target_profile,
        "inventory": _expression_inventory(expression),
        "risks": [risk.as_dict() for risk in risks],
        "risk_count": len(risks),
        "fidelity_ceiling": fidelity_ceiling.value,
        "behavioral_equivalence": "NOT_ESTABLISHED",
        "evidence_basis": "SQLGLOT_DIALECT_FLAGS",
    }


def combined_fidelity(
    capability_fidelity: TranslationFidelity,
    expression_semantics: dict[str, Any],
) -> TranslationFidelity:
    semantic_fidelity = TranslationFidelity(
        str(expression_semantics["fidelity_ceiling"])
    )
    return max(
        (capability_fidelity, semantic_fidelity),
        key=lambda value: value.severity,
    )
