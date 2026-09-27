import pytest

from sql_connectome.connectome import (
    DEFAULT_OPERATION_CATALOG,
    DeterminismClass,
    EvaluationClass,
    OperationKind,
    OperationSpec,
    inspect_operation_catalog,
    inspect_operation_graph,
    transpile_sql_text,
)


def _rows_by_semantic_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = payload["operations"]
    assert isinstance(rows, list)
    return {
        str(row["semantic_id"]): row
        for row in rows
        if row["semantic_id"] is not None
    }


def test_operation_catalog_is_source_controlled_and_digest_bound() -> None:
    payload = inspect_operation_catalog()

    assert payload["schema"] == "SQL_CONNECTOME_OPERATION_CATALOG_V1"
    assert payload["scope"] == "FUNCTIONS_AND_OPERATORS_ONLY"
    assert payload["operation_count"] >= 30
    assert len(payload["operation_catalog_digest"]) == 64
    assert payload["unmapped_meaning"] == "UNKNOWN_NOT_UNSUPPORTED"

    by_id = {row["semantic_id"]: row for row in payload["operations"]}
    assert by_id["arithmetic.divide"]["determinism"] == "DIALECT_DEPENDENT"
    assert by_id["aggregate.count"]["evaluation_class"] == "AGGREGATE"
    assert by_id["context.current_timestamp"]["determinism"] == "STATEMENT_STABLE"
    assert by_id["random.rand"]["determinism"] == "VOLATILE"
    assert all(row["authority_effect"] == "NONE" for row in payload["operations"])


def test_operation_catalog_rejects_expression_class_collisions() -> None:
    conflicting = OperationSpec(
        semantic_id="custom.alternate_add",
        canonical_name="ALTERNATE_ADD",
        kind=OperationKind.OPERATOR,
        family="custom",
        expression_classes=("Add",),
        evaluation_class=EvaluationClass.SCALAR,
        determinism=DeterminismClass.DETERMINISTIC,
    )

    with pytest.raises(ValueError, match="OPERATION_EXPRESSION_CLASS_COLLISION"):
        DEFAULT_OPERATION_CATALOG.admit(conflicting)


def test_query_operation_graph_maps_known_functions_and_operators() -> None:
    payload = inspect_operation_graph(
        "SELECT COUNT(*), COALESCE(a, 0), a / b FROM t WHERE a > 0",
        "postgresql",
    )

    assert payload["schema"] == "SQL_CONNECTOME_OPERATION_GRAPH_V1"
    assert payload["dialect_id"] == "postgresql"
    assert len(payload["operation_catalog_digest"]) == 64
    assert len(payload["catalog_digest"]) == 64
    assert payload["unmapped_occurrence_count"] == 0

    by_id = _rows_by_semantic_id(payload)
    assert "aggregate.count" in by_id
    assert "null.coalesce" in by_id
    assert "arithmetic.divide" in by_id
    assert "comparison.greater_than" in by_id
    assert by_id["arithmetic.divide"]["semantic_risk_codes"] == [
        "DIVISION_TYPE_SEMANTICS",
        "DIVISION_BY_ZERO_SEMANTICS",
    ]


def test_unknown_udf_remains_unmapped() -> None:
    payload = inspect_operation_graph("SELECT mystery_udf(a) FROM t", "postgresql")

    rows = payload["operations"]
    assert isinstance(rows, list)
    unknown = [row for row in rows if row["mapping_status"] == "UNMAPPED"]

    assert len(unknown) == 1
    assert unknown[0]["semantic_id"] is None
    assert unknown[0]["normalized_name"] == "MYSTERY_UDF"
    assert unknown[0]["determinism"] == "UNKNOWN"
    assert unknown[0]["authority_effect"] == "UNKNOWN"
    assert payload["unmapped_meaning"] == "UNKNOWN_NOT_UNSUPPORTED"


def test_semantic_risk_links_to_governed_operation_id() -> None:
    payload = transpile_sql_text(
        "SELECT numerator / denominator FROM measurements",
        "mysql",
        "postgresql",
        allow_lossy=True,
    )

    division_risks = [
        risk
        for risk in payload["expression_semantics"]["risks"]
        if risk["expression_family"] == "DIVISION"
    ]
    assert division_risks
    assert all(
        risk["semantic_operation_ids"] == ["arithmetic.divide"]
        for risk in division_risks
    )
