from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.dialects import Dialect


def _dtype_name(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, exp.DType):
        return value.value
    if isinstance(value, exp.DataType):
        return value.sql()
    return str(value)


def _expression_kind(node: exp.Expression) -> str:
    if isinstance(node, exp.DataType):
        return "TYPE"
    if isinstance(node, exp.Func):
        return "FUNCTION"

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
    if node.__class__.__name__ in operator_classes:
        return "OPERATOR"

    return "EXPRESSION"


def _expression_name(node: exp.Expression) -> str:
    if isinstance(node, exp.Func):
        sql_name = getattr(node, "sql_name", None)
        if callable(sql_name):
            return str(sql_name()).upper()
    return node.__class__.__name__.upper()


def _metadata_contract(
    node: exp.Expression,
    metadata_map: dict[type[exp.Expr], dict[str, Any]],
) -> dict[str, object]:
    metadata = metadata_map.get(type(node), {})
    fixed_return = _dtype_name(metadata.get("returns"))
    has_annotator = callable(metadata.get("annotator"))

    if fixed_return is not None:
        type_rule = "FIXED_RETURN"
    elif has_annotator:
        type_rule = "INFERRED"
    else:
        type_rule = "UNSPECIFIED"

    required = sorted(getattr(type(node), "required_args", set()))
    arg_types = getattr(type(node), "arg_types", {})
    optional = sorted(key for key in arg_types if key not in required)

    return {
        "expression_class": node.__class__.__name__,
        "expression_key": node.key,
        "name": _expression_name(node),
        "kind": _expression_kind(node),
        "required_args": required,
        "optional_args": optional,
        "variable_length_args": bool(getattr(type(node), "is_var_len_args", False)),
        "variable_length_arg_key": getattr(type(node), "var_len_arg_key", None),
        "type_rule": type_rule,
        "fixed_return_type": fixed_return,
        "dialect_metadata_present": bool(metadata),
    }


def _coercion_contract(dialect: Dialect) -> list[dict[str, object]]:
    coercions = getattr(dialect, "COERCES_TO", {})
    rows: list[dict[str, object]] = []

    for source, targets in coercions.items():
        source_name = _dtype_name(source)
        if source_name is None:
            continue
        target_names = sorted(
            name
            for target in targets
            if (name := _dtype_name(target)) is not None
        )
        rows.append(
            {
                "source_type": source_name,
                "target_types": target_names,
            }
        )

    rows.sort(key=lambda row: str(row["source_type"]))
    return rows


def expression_contracts(
    expression: exp.Expression,
    *,
    dialect_id: str,
    parser_dialect: str,
) -> dict[str, object]:
    dialect = Dialect.get_or_raise(parser_dialect)
    metadata_map = getattr(dialect, "EXPRESSION_METADATA", {})

    unique: dict[type[exp.Expression], exp.Expression] = {}
    counts: dict[type[exp.Expression], int] = {}

    for node in expression.walk():
        node_type = type(node)
        unique.setdefault(node_type, node)
        counts[node_type] = counts.get(node_type, 0) + 1

    contracts = []
    for node_type, node in unique.items():
        contract = _metadata_contract(node, metadata_map)
        contract["count"] = counts[node_type]
        contracts.append(contract)

    contracts.sort(
        key=lambda row: (
            str(row["kind"]),
            str(row["name"]),
            str(row["expression_class"]),
        )
    )

    return {
        "schema": "SQL_CONNECTOME_EXPRESSION_CONTRACTS_V1",
        "dialect_id": dialect_id,
        "parser_dialect": parser_dialect,
        "source": "SQLGLOT_EXPRESSION_METADATA",
        "sqlglot_version": sqlglot.__version__,
        "expression_contracts": contracts,
        "coercions": _coercion_contract(dialect),
        "behavioral_equivalence": "NOT_ESTABLISHED",
    }
