from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import sqlglot
from sqlglot import ErrorLevel, exp
from sqlglot.dialects import Dialect
from sqlglot.errors import ParseError, UnsupportedError

from .model import TranslationFidelity
from .registry import DEFAULT_DIALECTS


class CanonicalTypeFamily(StrEnum):
    NULL = "NULL"
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    FLOAT = "FLOAT"
    STRING = "STRING"
    BINARY = "BINARY"
    DATE = "DATE"
    TIME = "TIME"
    TIMESTAMP = "TIMESTAMP"
    INTERVAL = "INTERVAL"
    JSON = "JSON"
    ARRAY = "ARRAY"
    MAP = "MAP"
    STRUCT = "STRUCT"
    VARIANT = "VARIANT"
    UUID = "UUID"
    GEOSPATIAL = "GEOSPATIAL"
    VECTOR = "VECTOR"
    OTHER = "OTHER"


_TYPE_FAMILIES: dict[str, CanonicalTypeFamily] = {
    "NULL": CanonicalTypeFamily.NULL,
    "BOOLEAN": CanonicalTypeFamily.BOOLEAN,
    "BOOL": CanonicalTypeFamily.BOOLEAN,
    "TINYINT": CanonicalTypeFamily.INTEGER,
    "SMALLINT": CanonicalTypeFamily.INTEGER,
    "MEDIUMINT": CanonicalTypeFamily.INTEGER,
    "INT": CanonicalTypeFamily.INTEGER,
    "INTEGER": CanonicalTypeFamily.INTEGER,
    "BIGINT": CanonicalTypeFamily.INTEGER,
    "UTINYINT": CanonicalTypeFamily.INTEGER,
    "USMALLINT": CanonicalTypeFamily.INTEGER,
    "UINT": CanonicalTypeFamily.INTEGER,
    "UBIGINT": CanonicalTypeFamily.INTEGER,
    "INT128": CanonicalTypeFamily.INTEGER,
    "UINT128": CanonicalTypeFamily.INTEGER,
    "DECIMAL": CanonicalTypeFamily.DECIMAL,
    "DEC": CanonicalTypeFamily.DECIMAL,
    "NUMERIC": CanonicalTypeFamily.DECIMAL,
    "BIGNUMERIC": CanonicalTypeFamily.DECIMAL,
    "BIGDECIMAL": CanonicalTypeFamily.DECIMAL,
    "FLOAT": CanonicalTypeFamily.FLOAT,
    "FLOAT4": CanonicalTypeFamily.FLOAT,
    "FLOAT8": CanonicalTypeFamily.FLOAT,
    "REAL": CanonicalTypeFamily.FLOAT,
    "DOUBLE": CanonicalTypeFamily.FLOAT,
    "DOUBLE PRECISION": CanonicalTypeFamily.FLOAT,
    "CHAR": CanonicalTypeFamily.STRING,
    "NCHAR": CanonicalTypeFamily.STRING,
    "VARCHAR": CanonicalTypeFamily.STRING,
    "NVARCHAR": CanonicalTypeFamily.STRING,
    "TEXT": CanonicalTypeFamily.STRING,
    "TINYTEXT": CanonicalTypeFamily.STRING,
    "MEDIUMTEXT": CanonicalTypeFamily.STRING,
    "LONGTEXT": CanonicalTypeFamily.STRING,
    "STRING": CanonicalTypeFamily.STRING,
    "CLOB": CanonicalTypeFamily.STRING,
    "FIXEDSTRING": CanonicalTypeFamily.STRING,
    "BINARY": CanonicalTypeFamily.BINARY,
    "VARBINARY": CanonicalTypeFamily.BINARY,
    "BLOB": CanonicalTypeFamily.BINARY,
    "BYTEA": CanonicalTypeFamily.BINARY,
    "IMAGE": CanonicalTypeFamily.BINARY,
    "DATE": CanonicalTypeFamily.DATE,
    "TIME": CanonicalTypeFamily.TIME,
    "TIMETZ": CanonicalTypeFamily.TIME,
    "DATETIME": CanonicalTypeFamily.TIMESTAMP,
    "DATETIME2": CanonicalTypeFamily.TIMESTAMP,
    "SMALLDATETIME": CanonicalTypeFamily.TIMESTAMP,
    "TIMESTAMP": CanonicalTypeFamily.TIMESTAMP,
    "TIMESTAMPTZ": CanonicalTypeFamily.TIMESTAMP,
    "TIMESTAMPNTZ": CanonicalTypeFamily.TIMESTAMP,
    "TIMESTAMPLTZ": CanonicalTypeFamily.TIMESTAMP,
    "INTERVAL": CanonicalTypeFamily.INTERVAL,
    "JSON": CanonicalTypeFamily.JSON,
    "JSONB": CanonicalTypeFamily.JSON,
    "ARRAY": CanonicalTypeFamily.ARRAY,
    "MAP": CanonicalTypeFamily.MAP,
    "STRUCT": CanonicalTypeFamily.STRUCT,
    "ROW": CanonicalTypeFamily.STRUCT,
    "OBJECT": CanonicalTypeFamily.STRUCT,
    "VARIANT": CanonicalTypeFamily.VARIANT,
    "UUID": CanonicalTypeFamily.UUID,
    "GEOGRAPHY": CanonicalTypeFamily.GEOSPATIAL,
    "GEOMETRY": CanonicalTypeFamily.GEOSPATIAL,
    "VECTOR": CanonicalTypeFamily.VECTOR,
}


@dataclass(frozen=True, slots=True)
class TypeProjectionRisk:
    code: str
    source_type: str
    target_type: str | None
    source_family: CanonicalTypeFamily
    target_family: CanonicalTypeFamily | None
    description: str
    fidelity: TranslationFidelity

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "source_family": self.source_family.value,
            "target_family": self.target_family.value if self.target_family else None,
            "description": self.description,
            "fidelity": self.fidelity.value,
        }


def _dtype_name(value: object) -> str:
    if isinstance(value, exp.DType):
        return value.value.upper()
    text = str(value).upper()
    if text.startswith("DTYPE."):
        text = text.removeprefix("DTYPE.")
    return text


def canonical_type_family(value: object) -> CanonicalTypeFamily:
    return _TYPE_FAMILIES.get(_dtype_name(value), CanonicalTypeFamily.OTHER)


def _type_parameters(node: exp.DataType, parser_dialect: str) -> tuple[str, ...]:
    return tuple(
        parameter.sql(dialect=parser_dialect)
        for parameter in node.expressions
    )


def _coercion_fidelity(
    source_type: str,
    target_type: str,
    source_family: CanonicalTypeFamily,
    target_family: CanonicalTypeFamily,
) -> tuple[TranslationFidelity, str]:
    if source_type == target_type:
        return TranslationFidelity.EXACT, "IDENTICAL_DIALECT_TYPE"

    if source_family == target_family:
        return TranslationFidelity.CONSTRUCTIVE, "SAME_CANONICAL_FAMILY"

    if (
        source_family is CanonicalTypeFamily.INTEGER
        and target_family is CanonicalTypeFamily.DECIMAL
    ):
        return TranslationFidelity.CONSTRUCTIVE, "NUMERIC_WIDENING"

    if (
        source_family in {CanonicalTypeFamily.INTEGER, CanonicalTypeFamily.DECIMAL}
        and target_family is CanonicalTypeFamily.FLOAT
    ):
        return TranslationFidelity.LOSSY, "BINARY_FLOAT_PRECISION_RISK"

    if (
        source_family is CanonicalTypeFamily.DATE
        and target_family is CanonicalTypeFamily.TIMESTAMP
    ):
        return TranslationFidelity.CONSTRUCTIVE, "TEMPORAL_WIDENING"

    return TranslationFidelity.LOSSY, "CROSS_FAMILY_COERCION"


def dialect_type_graph(
    *,
    dialect_id: str,
    parser_dialect: str,
) -> dict[str, object]:
    dialect = Dialect.get_or_raise(parser_dialect)
    coercions = getattr(dialect, "COERCES_TO", {})

    dialect_types: dict[str, CanonicalTypeFamily] = {}
    edges: list[dict[str, object]] = []

    for source, targets in coercions.items():
        source_name = _dtype_name(source)
        source_family = canonical_type_family(source)
        dialect_types[source_name] = source_family

        for target in targets:
            target_name = _dtype_name(target)
            target_family = canonical_type_family(target)
            dialect_types[target_name] = target_family
            fidelity, risk_class = _coercion_fidelity(
                source_name,
                target_name,
                source_family,
                target_family,
            )
            edges.append(
                {
                    "source_type": source_name,
                    "target_type": target_name,
                    "source_family": source_family.value,
                    "target_family": target_family.value,
                    "mode": "IMPLICIT_DEPENDENCY_EVIDENCE",
                    "fidelity": fidelity.value,
                    "fidelity_scope": "COERCION_SHAPE_ONLY",
                    "risk_class": risk_class,
                }
            )

    nodes = [
        {
            "dialect_type": name,
            "canonical_family": family.value,
        }
        for name, family in sorted(dialect_types.items())
    ]
    edges.sort(
        key=lambda row: (
            str(row["source_type"]),
            str(row["target_type"]),
        )
    )

    return {
        "schema": "SQL_CONNECTOME_TYPE_GRAPH_V1",
        "dialect_id": dialect_id,
        "parser_dialect": parser_dialect,
        "sqlglot_version": sqlglot.__version__,
        "canonical_families": [family.value for family in CanonicalTypeFamily],
        "dialect_types": nodes,
        "implicit_coercions": edges,
        "evidence_basis": "SQLGLOT_COERCES_TO",
        "evidence_ceiling": "DEPENDENCY_METADATA",
        "fidelity_scope": "COERCION_SHAPE_ONLY",
        "missing_edge_meaning": "UNKNOWN_NOT_UNSUPPORTED",
        "behavioral_equivalence": "NOT_ESTABLISHED",
    }


def _project_explicit_type(
    node: exp.DataType,
    *,
    target_dialect: str,
    source_parser_dialect: str,
    target_parser_dialect: str,
    target_capabilities: frozenset[str] | None = None,
) -> tuple[dict[str, object], TypeProjectionRisk | None]:
    source_sql = node.sql(dialect=source_parser_dialect)
    source_family = canonical_type_family(node.this)
    source_parameters = _type_parameters(node, source_parser_dialect)

    capabilities = (
        target_capabilities
        if target_capabilities is not None
        else DEFAULT_DIALECTS[target_dialect].capabilities
    )
    if (
        source_family is CanonicalTypeFamily.VARIANT
        and "variant" not in capabilities
        and "json" in capabilities
    ):
        risk = TypeProjectionRisk(
            code="VARIANT_TO_JSON_REPRESENTATION",
            source_type=source_sql,
            target_type="JSON",
            source_family=source_family,
            target_family=CanonicalTypeFamily.JSON,
            description=(
                "The target lacks admitted VARIANT capability; JSON can preserve data "
                "representation but not source VARIANT typing/coercion semantics."
            ),
            fidelity=TranslationFidelity.LOSSY,
        )
        return (
            {
                "source_type": source_sql,
                "target_type": "JSON",
                "source_family": source_family.value,
                "target_family": CanonicalTypeFamily.JSON.value,
                "source_parameters": list(source_parameters),
                "target_parameters": [],
                "projection": "ADMITTED_REPRESENTATION_RULE",
                "fidelity": TranslationFidelity.LOSSY.value,
            },
            risk,
        )

    if (
        source_family is CanonicalTypeFamily.STRUCT
        and "structs" not in capabilities
        and "json" in capabilities
    ):
        risk = TypeProjectionRisk(
            code="STRUCT_TO_JSON_REPRESENTATION",
            source_type=source_sql,
            target_type="JSON",
            source_family=source_family,
            target_family=CanonicalTypeFamily.JSON,
            description=(
                "The target lacks admitted STRUCT capability; JSON is a representation "
                "fallback and does not prove equivalent field typing/coercion semantics."
            ),
            fidelity=TranslationFidelity.LOSSY,
        )
        return (
            {
                "source_type": source_sql,
                "target_type": "JSON",
                "source_family": source_family.value,
                "target_family": CanonicalTypeFamily.JSON.value,
                "source_parameters": list(source_parameters),
                "target_parameters": [],
                "projection": "ADMITTED_REPRESENTATION_RULE",
                "fidelity": TranslationFidelity.LOSSY.value,
            },
            risk,
        )

    try:
        target_sql = node.sql(
            dialect=target_parser_dialect,
            unsupported_level=ErrorLevel.RAISE,
        )
        target_node = exp.DataType.build(target_sql, dialect=target_parser_dialect)
    except (UnsupportedError, ParseError, ValueError, TypeError):
        risk = TypeProjectionRisk(
            code="TYPE_UNREPRESENTABLE",
            source_type=source_sql,
            target_type=None,
            source_family=source_family,
            target_family=None,
            description="The explicit source type could not be represented by the target adapter.",
            fidelity=TranslationFidelity.UNREPRESENTABLE,
        )
        return (
            {
                "source_type": source_sql,
                "target_type": None,
                "source_family": source_family.value,
                "target_family": None,
                "source_parameters": list(source_parameters),
                "target_parameters": [],
                "projection": "UNREPRESENTABLE",
                "fidelity": TranslationFidelity.UNREPRESENTABLE.value,
            },
            risk,
        )

    target_family = canonical_type_family(target_node.this)
    target_parameters = _type_parameters(target_node, target_parser_dialect)

    risk: TypeProjectionRisk | None = None
    fidelity = TranslationFidelity.EXACT
    projection = "CANONICAL_FAMILY_PRESERVED"

    if source_family != target_family:
        fidelity = TranslationFidelity.LOSSY
        projection = "CANONICAL_FAMILY_CHANGED"
        risk = TypeProjectionRisk(
            code="TYPE_FAMILY_CHANGE",
            source_type=source_sql,
            target_type=target_sql,
            source_family=source_family,
            target_family=target_family,
            description=(
                "Source and target adapters place the explicit type in different "
                "canonical semantic families."
            ),
            fidelity=fidelity,
        )
    elif source_parameters and source_parameters != target_parameters:
        fidelity = TranslationFidelity.LOSSY
        projection = "TYPE_PARAMETERS_CHANGED"
        risk = TypeProjectionRisk(
            code="TYPE_PARAMETER_CHANGE",
            source_type=source_sql,
            target_type=target_sql,
            source_family=source_family,
            target_family=target_family,
            description=(
                "The target representation changed explicit type parameters such as "
                "length, precision, scale, or nested type arguments."
            ),
            fidelity=fidelity,
        )

    return (
        {
            "source_type": source_sql,
            "target_type": target_sql,
            "source_family": source_family.value,
            "target_family": target_family.value,
            "source_parameters": list(source_parameters),
            "target_parameters": list(target_parameters),
            "projection": projection,
            "fidelity": fidelity.value,
        },
        risk,
    )


def assess_type_semantics(
    expression: exp.Expression,
    *,
    source_dialect: str,
    target_dialect: str,
    source_parser_dialect: str,
    target_parser_dialect: str,
    target_capabilities: frozenset[str] | None = None,
) -> dict[str, Any]:
    projections: list[dict[str, object]] = []
    risks: list[TypeProjectionRisk] = []

    for node in expression.walk():
        if not isinstance(node, exp.DataType):
            continue
        projection, risk = _project_explicit_type(
            node,
            target_dialect=target_dialect,
            source_parser_dialect=source_parser_dialect,
            target_parser_dialect=target_parser_dialect,
            target_capabilities=target_capabilities,
        )
        projections.append(projection)
        if risk is not None:
            risks.append(risk)

    ceiling = TranslationFidelity.EXACT
    for risk in risks:
        if risk.fidelity.severity > ceiling.severity:
            ceiling = risk.fidelity

    source_graph = dialect_type_graph(
        dialect_id=source_dialect,
        parser_dialect=source_parser_dialect,
    )
    target_graph = dialect_type_graph(
        dialect_id=target_dialect,
        parser_dialect=target_parser_dialect,
    )

    return {
        "schema": "SQL_CONNECTOME_TYPE_SEMANTICS_V1",
        "source_dialect": source_dialect,
        "target_dialect": target_dialect,
        "coverage": "EXPLICIT_TYPES_ONLY",
        "fidelity_scope": "EXPLICIT_TYPE_CANONICAL_FAMILY",
        "projections": projections,
        "risks": [risk.as_dict() for risk in risks],
        "risk_count": len(risks),
        "fidelity_ceiling": ceiling.value,
        "coercion_graph_evidence": {
            "source_edge_count": len(source_graph["implicit_coercions"]),
            "target_edge_count": len(target_graph["implicit_coercions"]),
            "evidence_basis": "SQLGLOT_COERCES_TO",
            "evidence_ceiling": "DEPENDENCY_METADATA",
        },
        "behavioral_equivalence": "NOT_ESTABLISHED",
    }



def rewrite_type_representations(
    expression: exp.Expression,
    *,
    target_dialect: str,
    target_parser_dialect: str,
    target_capabilities: frozenset[str] | None = None,
) -> exp.Expression:
    capabilities = (
        target_capabilities
        if target_capabilities is not None
        else DEFAULT_DIALECTS[target_dialect].capabilities
    )

    def rewrite(node: exp.Expression) -> exp.Expression:
        if not isinstance(node, exp.DataType):
            return node

        family = canonical_type_family(node.this)
        if (
            family is CanonicalTypeFamily.VARIANT
            and "variant" not in capabilities
            and "json" in capabilities
        ):
            return exp.DataType.build("JSON", dialect=target_parser_dialect)

        if (
            family is CanonicalTypeFamily.STRUCT
            and "structs" not in capabilities
            and "json" in capabilities
        ):
            return exp.DataType.build("JSON", dialect=target_parser_dialect)

        return node

    return expression.transform(rewrite, copy=True)
