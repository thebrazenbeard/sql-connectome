from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sql_connectome.receipts import canonical_digest


class Nullability(StrEnum):
    NULLABLE = "NULLABLE"
    NON_NULL = "NON_NULL"
    UNKNOWN = "UNKNOWN"


class Multiplicity(StrEnum):
    BAG = "BAG"
    SET = "SET"


class CardinalityCertainty(StrEnum):
    PROVEN = "PROVEN"
    DERIVED = "DERIVED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class LogicalType:
    canonical_family: str
    source_spelling: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "canonical_family": self.canonical_family,
            "source_spelling": self.source_spelling,
        }


@dataclass(frozen=True, slots=True)
class LogicalField:
    field_id: str
    name: str
    logical_type: LogicalType
    nullability: Nullability = Nullability.UNKNOWN
    provenance: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "name": self.name,
            "logical_type": self.logical_type.as_dict(),
            "nullability": self.nullability.value,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class LogicalSchema:
    fields: tuple[LogicalField, ...]

    def validate(self) -> None:
        ids = [field.field_id for field in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_LOGICAL_FIELD_ID")

    def as_dict(self) -> list[dict[str, Any]]:
        return [field.as_dict() for field in self.fields]


@dataclass(frozen=True, slots=True)
class CardinalityBounds:
    minimum: int | None = None
    maximum: int | None = None
    certainty: CardinalityCertainty = CardinalityCertainty.UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {
            "minimum": self.minimum,
            "maximum": self.maximum,
            "certainty": self.certainty.value,
        }


@dataclass(frozen=True, slots=True)
class LogicalExpression:
    expression_id: str
    kind: str
    logical_type: LogicalType
    nullability: Nullability = Nullability.UNKNOWN
    scope_id: str | None = None
    outer_scope_id: str | None = None
    source_sql: str | None = None
    evidence: tuple[str, ...] = ()
    field_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "expression_id": self.expression_id,
            "kind": self.kind,
            "logical_type": self.logical_type.as_dict(),
            "nullability": self.nullability.value,
            "scope_id": self.scope_id,
            "outer_scope_id": self.outer_scope_id,
            "source_sql": self.source_sql,
            "evidence": list(self.evidence),
            "field_id": self.field_id,
        }


@dataclass(frozen=True, slots=True)
class LogicalRelation:
    relation_id: str
    kind: str
    output_schema: LogicalSchema
    cardinality: CardinalityBounds
    inputs: tuple[str, ...] = ()
    scope_id: str | None = None
    multiplicity: Multiplicity = Multiplicity.BAG

    def as_dict(self) -> dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "kind": self.kind,
            "output_schema": self.output_schema.as_dict(),
            "cardinality": self.cardinality.as_dict(),
            "inputs": list(self.inputs),
            "scope_id": self.scope_id,
            "multiplicity": self.multiplicity.value,
        }


@dataclass(frozen=True, slots=True)
class LogicalPlan:
    roots: tuple[str, ...]
    relations: tuple[LogicalRelation, ...]
    source_ir_digest: str
    bound_ir_digest: str
    schema_digest: str
    expressions: tuple[LogicalExpression, ...] = ()
    losses: tuple[str, ...] = ()

    def validate(self) -> None:
        ids = [relation.relation_id for relation in self.relations]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_LOGICAL_RELATION_ID")
        known = set(ids)
        if any(root not in known for root in self.roots):
            raise ValueError("UNKNOWN_LOGICAL_ROOT")
        for relation in self.relations:
            relation.output_schema.validate()
            if any(item not in known for item in relation.inputs):
                raise ValueError("DANGLING_LOGICAL_INPUT")
        expression_ids = [item.expression_id for item in self.expressions]
        if len(expression_ids) != len(set(expression_ids)):
            raise ValueError("DUPLICATE_LOGICAL_EXPRESSION_ID")
        known_fields = {
            field.field_id
            for relation in self.relations
            for field in relation.output_schema.fields
        }
        if any(
            item.field_id is not None and item.field_id not in known_fields
            for item in self.expressions
        ):
            raise ValueError("DANGLING_LOGICAL_FIELD_REFERENCE")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_LOGICAL_PLAN_V1",
            "roots": list(self.roots),
            "relations": [relation.as_dict() for relation in self.relations],
            "expressions": [expression.as_dict() for expression in self.expressions],
            "losses": list(self.losses),
            "source_ir_digest": self.source_ir_digest,
            "bound_ir_digest": self.bound_ir_digest,
            "schema_digest": self.schema_digest,
        }


def logical_plan_digest(plan: LogicalPlan) -> str:
    plan.validate()
    return canonical_digest(plan.as_dict())
