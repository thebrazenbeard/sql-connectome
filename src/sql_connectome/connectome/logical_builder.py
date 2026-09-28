from __future__ import annotations

from sqlglot import exp

from .logical_plan import (
    CardinalityBounds,
    CardinalityCertainty,
    LogicalField,
    LogicalPlan,
    LogicalRelation,
    LogicalSchema,
    LogicalType,
    Multiplicity,
    Nullability,
)
from .type_system import canonical_type_family


def _logical_type(expression: exp.Expression) -> LogicalType:
    value = expression.type
    spelling = (
        value.sql() if value is not None and hasattr(value, "sql") else str(value or "UNKNOWN")
    )
    family = "UNKNOWN" if spelling.upper() == "UNKNOWN" else canonical_type_family(spelling).value
    return LogicalType(family, spelling)


def _field(field_id: str, name: str, expression: exp.Expression) -> LogicalField:
    return LogicalField(
        field_id,
        name,
        _logical_type(expression),
        Nullability.UNKNOWN,
        (f"bound-expression:{expression.sql()}",),
    )


def build_logical_plan(
    typed: exp.Expression,
    *,
    dialect_id: str,
    source_ir_digest: str,
    bound_ir_digest: str,
    schema_digest: str,
) -> LogicalPlan:
    if isinstance(typed, exp.Union):
        left = build_logical_plan(
            typed.this,
            dialect_id=dialect_id,
            source_ir_digest=source_ir_digest,
            bound_ir_digest=bound_ir_digest,
            schema_digest=schema_digest,
        )
        right = build_logical_plan(
            typed.expression,
            dialect_id=dialect_id,
            source_ir_digest=source_ir_digest,
            bound_ir_digest=bound_ir_digest,
            schema_digest=schema_digest,
        )

        def renamed(plan: LogicalPlan, prefix: str) -> tuple[LogicalRelation, ...]:
            mapping = {item.relation_id: f"{prefix}:{item.relation_id}" for item in plan.relations}
            return tuple(
                LogicalRelation(
                    mapping[item.relation_id],
                    item.kind,
                    item.output_schema,
                    item.cardinality,
                    tuple(mapping[value] for value in item.inputs),
                    f"{prefix}:{item.scope_id}" if item.scope_id else None,
                    item.multiplicity,
                )
                for item in plan.relations
            )

        left_relations = renamed(left, "left")
        right_relations = renamed(right, "right")
        output = left_relations[-1].output_schema
        if len(output.fields) != len(right_relations[-1].output_schema.fields):
            raise ValueError("SET_OP_ARITY_MISMATCH")
        set_op = LogicalRelation(
            "relation:set-op:0",
            "SET_OP",
            output,
            CardinalityBounds(certainty=CardinalityCertainty.UNKNOWN),
            inputs=(left_relations[-1].relation_id, right_relations[-1].relation_id),
            multiplicity=Multiplicity.BAG
            if typed.args.get("distinct") is False
            else Multiplicity.SET,
        )
        plan = LogicalPlan(
            ("relation:set-op:0",),
            left_relations + right_relations + (set_op,),
            source_ir_digest,
            bound_ir_digest,
            schema_digest,
        )
        plan.validate()
        return plan

    if not isinstance(typed, exp.Select):
        raise ValueError("LOGICAL_PLAN_SELECT_ONLY")

    relations: list[LogicalRelation] = []
    from_clause = typed.args.get("from_")
    table = next(from_clause.find_all(exp.Table), None) if from_clause is not None else None
    if table is None:
        raise ValueError("LOGICAL_PLAN_READ_SOURCE_REQUIRED")

    read_fields = tuple(
        _field(f"field:read:{index}:{column.name}", column.name, column)
        for index, column in enumerate(typed.find_all(exp.Column))
        if column.table == table.alias_or_name
    )
    if not read_fields:
        read_fields = tuple(
            _field(f"field:read:{index}:{column.name}", column.name, column)
            for index, column in enumerate(typed.find_all(exp.Column))
        )
    current_id = "relation:read:0"
    relations.append(
        LogicalRelation(
            current_id,
            "READ",
            LogicalSchema(read_fields),
            CardinalityBounds(certainty=CardinalityCertainty.UNKNOWN),
            scope_id="scope:select:0",
        )
    )

    where_clause = typed.args.get("where")
    nested_selects = list(where_clause.find_all(exp.Select)) if where_clause is not None else []
    for index, _nested in enumerate(nested_selects):
        subquery_id = f"relation:subquery:{index}"
        relations.append(
            LogicalRelation(
                subquery_id,
                "SUBQUERY",
                LogicalSchema(()),
                CardinalityBounds(certainty=CardinalityCertainty.UNKNOWN),
                inputs=(current_id,),
                scope_id=f"scope:subquery:{index}",
            )
        )

    if where_clause is not None:
        filter_id = "relation:filter:0"
        relations.append(
            LogicalRelation(
                filter_id,
                "FILTER",
                relations[0].output_schema,
                relations[0].cardinality,
                inputs=(current_id,),
                scope_id="scope:select:0",
            )
        )
        current_id = filter_id

    has_aggregate = any(
        isinstance(node, exp.AggFunc)
        for projection in typed.expressions
        for node in projection.walk()
    )
    if has_aggregate:
        aggregate_id = "relation:aggregate:0"
        grouped = typed.args.get("group") is not None
        relations.append(
            LogicalRelation(
                aggregate_id,
                "AGGREGATE",
                relations[-1].output_schema,
                CardinalityBounds(
                    minimum=0 if grouped else 1,
                    maximum=None if grouped else 1,
                    certainty=CardinalityCertainty.DERIVED,
                ),
                inputs=(current_id,),
                scope_id="scope:select:0",
            )
        )
        current_id = aggregate_id

    nullable_tables = {
        join.this.alias_or_name
        for join in typed.args.get("joins") or ()
        if (join.args.get("side") or "").upper() in {"LEFT", "FULL"}
    }

    projection_fields = []
    for index, projection in enumerate(typed.expressions):
        field = _field(
            f"field:project:{index}:{projection.alias_or_name or index}",
            projection.alias_or_name or projection.sql(),
            projection,
        )
        column = projection.this if isinstance(projection, exp.Alias) else projection
        if isinstance(column, exp.Column) and column.table in nullable_tables:
            field = LogicalField(
                field.field_id,
                field.name,
                field.logical_type,
                Nullability.NULLABLE,
                field.provenance,
            )
        projection_fields.append(field)
    projection_fields = tuple(projection_fields)
    project_id = "relation:project:0"
    relations.append(
        LogicalRelation(
            project_id,
            "PROJECT",
            LogicalSchema(projection_fields),
            relations[-1].cardinality,
            inputs=(current_id,),
            scope_id="scope:select:0",
        )
    )
    current_id = project_id

    limit = typed.args.get("limit")
    if limit is not None:
        expression = limit.expression
        maximum = (
            int(expression.this)
            if isinstance(expression, exp.Literal) and expression.is_int
            else None
        )
        limit_id = "relation:limit:0"
        relations.append(
            LogicalRelation(
                limit_id,
                "LIMIT",
                relations[-1].output_schema,
                CardinalityBounds(
                    minimum=0,
                    maximum=maximum,
                    certainty=(
                        CardinalityCertainty.DERIVED
                        if maximum is not None
                        else CardinalityCertainty.UNKNOWN
                    ),
                ),
                inputs=(current_id,),
                scope_id="scope:select:0",
            )
        )
        current_id = limit_id

    plan = LogicalPlan(
        roots=(current_id,),
        relations=tuple(relations),
        source_ir_digest=source_ir_digest,
        bound_ir_digest=bound_ir_digest,
        schema_digest=schema_digest,
    )
    plan.validate()
    return plan
