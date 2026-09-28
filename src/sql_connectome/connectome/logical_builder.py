from __future__ import annotations

from sqlglot import exp

from .logical_plan import (
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

        def renamed_expressions(
            plan: LogicalPlan, prefix: str
        ) -> tuple[LogicalExpression, ...]:
            return tuple(
                LogicalExpression(
                    f"{prefix}:{item.expression_id}",
                    item.kind,
                    item.logical_type,
                    item.nullability,
                    f"{prefix}:{item.scope_id}" if item.scope_id else None,
                    f"{prefix}:{item.outer_scope_id}" if item.outer_scope_id else None,
                    item.source_sql,
                    item.evidence,
                )
                for item in plan.expressions
            )

        left_relations = renamed(left, "left")
        right_relations = renamed(right, "right")
        left_expressions = renamed_expressions(left, "left")
        right_expressions = renamed_expressions(right, "right")
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
            expressions=left_expressions + right_expressions,
            losses=(
                *left.losses,
                *right.losses,
                "SET_OP_TYPE_RECONCILIATION_UNQUALIFIED_V1",
            ),
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

    def read_relation(source: exp.Table, index: int) -> LogicalRelation:
        alias = source.alias_or_name
        fields = tuple(
            _field(f"field:read:{index}:{field_index}:{column.name}", column.name, column)
            for field_index, column in enumerate(typed.find_all(exp.Column))
            if column.table == alias
        )
        if not fields and index == 0:
            fields = tuple(
                _field(f"field:read:{index}:{field_index}:{column.name}", column.name, column)
                for field_index, column in enumerate(typed.find_all(exp.Column))
                if not column.table
            )
        return LogicalRelation(
            f"relation:read:{index}",
            "READ",
            LogicalSchema(fields),
            CardinalityBounds(certainty=CardinalityCertainty.UNKNOWN),
            scope_id="scope:select:0",
        )

    first_read = read_relation(table, 0)
    relations.append(first_read)
    current_id = first_read.relation_id

    for join_index, join in enumerate(typed.args.get("joins") or ()):
        join_table = join.this if isinstance(join.this, exp.Table) else None
        if join_table is None:
            raise ValueError("LOGICAL_PLAN_JOIN_SOURCE_UNREPRESENTABLE")
        right_read = read_relation(join_table, join_index + 1)
        relations.append(right_read)
        side = (join.args.get("side") or "").upper()
        current_relation = next(item for item in relations if item.relation_id == current_id)
        left_fields = list(current_relation.output_schema.fields)
        right_fields = list(right_read.output_schema.fields)
        if side in {"RIGHT", "FULL"}:
            left_fields = [
                LogicalField(f.field_id, f.name, f.logical_type, Nullability.NULLABLE, f.provenance)
                for f in left_fields
            ]
        if side in {"LEFT", "FULL"}:
            right_fields = [
                LogicalField(f.field_id, f.name, f.logical_type, Nullability.NULLABLE, f.provenance)
                for f in right_fields
            ]
        join_id = f"relation:join:{join_index}"
        relations.append(
            LogicalRelation(
                join_id,
                "JOIN",
                LogicalSchema(tuple(left_fields + right_fields)),
                CardinalityBounds(certainty=CardinalityCertainty.UNKNOWN),
                inputs=(current_id, right_read.relation_id),
                scope_id="scope:select:0",
            )
        )
        current_id = join_id

    where_clause = typed.args.get("where")
    nested_selects = list(where_clause.find_all(exp.Select)) if where_clause is not None else []
    subquery_ids: list[str] = []
    for index, _nested in enumerate(nested_selects):
        subquery_id = f"relation:subquery:{index}"
        subquery_ids.append(subquery_id)
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
        current_relation = next(item for item in relations if item.relation_id == current_id)
        relations.append(
            LogicalRelation(
                filter_id,
                "FILTER",
                current_relation.output_schema,
                current_relation.cardinality,
                inputs=(current_id, *subquery_ids),
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

    nullable_tables: set[str] = set()
    seen_tables = {table.alias_or_name}
    for join in typed.args.get("joins") or ():
        if not isinstance(join.this, exp.Table):
            continue
        joined_alias = join.this.alias_or_name
        side = (join.args.get("side") or "").upper()
        if side in {"LEFT", "FULL"}:
            nullable_tables.add(joined_alias)
        if side in {"RIGHT", "FULL"}:
            nullable_tables.update(seen_tables)
        seen_tables.add(joined_alias)

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

    outer_aliases = {table.alias_or_name} | {
        join.this.alias_or_name
        for join in typed.args.get("joins") or ()
        if isinstance(join.this, exp.Table)
    }
    expressions: list[LogicalExpression] = []
    for index, column in enumerate(typed.find_all(exp.Column)):
        owner = column.find_ancestor(exp.Select)
        is_nested = owner is not None and owner is not typed
        nested_aliases = (
            {item.alias_or_name for item in owner.find_all(exp.Table)}
            if is_nested and owner is not None
            else set()
        )
        correlated = (
            is_nested
            and bool(column.table)
            and column.table not in nested_aliases
            and (column.table in outer_aliases or bool(outer_aliases))
        )
        nested_scope_index = (\n            next(\n                (i for i, candidate in enumerate(nested_selects) if candidate is owner),\n                0,\n            )\n            if is_nested\n            else None\n        )\n        scope_id = (\n            f"scope:subquery:{nested_scope_index}"\n            if is_nested\n            else "scope:select:0"\n        )
        expressions.append(
            LogicalExpression(
                expression_id=f"expression:column:{index}:{column.sql()}",
                kind="FIELD_REFERENCE",
                logical_type=_logical_type(column),
                nullability=Nullability.UNKNOWN,
                scope_id=scope_id,
                outer_scope_id="scope:select:0" if correlated else None,
                source_sql=column.sql(),
                evidence=("bound-column-reference",),
            )
        )

    losses: list[str] = []
    if typed.args.get("order") is not None:
        losses.append("SORT_NOT_DERIVED_V1")
    if typed.args.get("distinct") is not None:
        losses.append("DISTINCT_NOT_DERIVED_V1")
    if any(isinstance(node, exp.Window) for node in typed.walk()):
        losses.append("WINDOW_NOT_DERIVED_V1")

    plan = LogicalPlan(
        roots=(current_id,),
        relations=tuple(relations),
        source_ir_digest=source_ir_digest,
        bound_ir_digest=bound_ir_digest,
        schema_digest=schema_digest,
        expressions=tuple(expressions),
        losses=tuple(losses),
    )
    plan.validate()
    return plan
