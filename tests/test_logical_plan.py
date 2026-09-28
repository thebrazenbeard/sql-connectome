from sql_connectome.connectome.logical_plan import (
    CardinalityBounds,
    CardinalityCertainty,
    LogicalExpression,
    LogicalField,
    LogicalPlan,
    LogicalRelation,
    LogicalSchema,
    LogicalType,
    Multiplicity,
    Nullability,
    logical_plan_digest,
)


def test_logical_plan_defaults_to_bag_and_has_deterministic_digest():
    field = LogicalField(
        "f:id", "id", LogicalType("INTEGER", "INT"), Nullability.UNKNOWN, ("schema:users.id",)
    )
    read = LogicalRelation(
        "r:users",
        "READ",
        LogicalSchema((field,)),
        CardinalityBounds(certainty=CardinalityCertainty.UNKNOWN),
    )
    plan = LogicalPlan(("r:users",), (read,), "a" * 64, "b" * 64, "c" * 64)
    plan.validate()
    assert read.multiplicity is Multiplicity.BAG
    assert field.nullability is Nullability.UNKNOWN
    assert logical_plan_digest(plan) == logical_plan_digest(plan)


def test_logical_plan_rejects_duplicate_and_dangling_relations():
    import pytest

    relation = LogicalRelation(
        "r", "VALUES", LogicalSchema(()), CardinalityBounds(0, 0, CardinalityCertainty.PROVEN)
    )
    duplicate = LogicalPlan(("r",), (relation, relation), "a", "b", "c")
    with pytest.raises(ValueError, match="DUPLICATE_LOGICAL_RELATION_ID"):
        duplicate.validate()
    dangling = LogicalRelation(
        "x", "PROJECT", LogicalSchema(()), CardinalityBounds(), inputs=("missing",)
    )
    plan = LogicalPlan(("x",), (dangling,), "a", "b", "c")
    with pytest.raises(ValueError, match="DANGLING_LOGICAL_INPUT"):
        plan.validate()


def test_logical_schema_rejects_duplicate_field_identity():
    import pytest

    field = LogicalField("f", "id", LogicalType("INTEGER"))
    with pytest.raises(ValueError, match="DUPLICATE_LOGICAL_FIELD_ID"):
        LogicalSchema((field, field)).validate()


def test_plan_rejects_dangling_field_reference():
    schema = LogicalSchema(
        (LogicalField("field:known", "id", LogicalType("INTEGER", "INT")),)
    )
    relation = LogicalRelation(
        "relation:read:0",
        "READ",
        schema,
        CardinalityBounds(),
    )
    expression = LogicalExpression(
        "expression:0",
        "FIELD_REFERENCE",
        LogicalType("INTEGER", "INT"),
        field_id="field:missing",
    )
    plan = LogicalPlan(
        ("relation:read:0",),
        (relation,),
        "source",
        "bound",
        "schema",
        expressions=(expression,),
    )
    with pytest.raises(ValueError, match="DANGLING_LOGICAL_FIELD_REFERENCE"):
        plan.validate()
