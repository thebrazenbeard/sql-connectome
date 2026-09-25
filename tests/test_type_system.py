from sql_connectome.connectome import (
    CanonicalTypeFamily,
    canonical_type_family,
    inspect_type_system,
    transpile_sql_text,
)


def test_canonical_type_families_normalize_common_aliases() -> None:
    assert canonical_type_family("INT") is CanonicalTypeFamily.INTEGER
    assert canonical_type_family("BIGINT") is CanonicalTypeFamily.INTEGER
    assert canonical_type_family("JSONB") is CanonicalTypeFamily.JSON
    assert canonical_type_family("TIMESTAMPTZ") is CanonicalTypeFamily.TIMESTAMP


def test_type_graph_is_dependency_evidence_not_engine_proof() -> None:
    graph = inspect_type_system("postgresql")

    assert graph["schema"] == "SQL_CONNECTOME_TYPE_GRAPH_V1"
    assert graph["dialect_id"] == "postgresql"
    assert graph["evidence_basis"] == "SQLGLOT_COERCES_TO"
    assert graph["evidence_ceiling"] == "DEPENDENCY_METADATA"
    assert graph["missing_edge_meaning"] == "UNKNOWN_NOT_UNSUPPORTED"
    assert graph["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert "INTEGER" in graph["canonical_families"]
    assert isinstance(graph["dialect_types"], list)
    assert isinstance(graph["implicit_coercions"], list)


def test_explicit_decimal_type_preserves_canonical_family() -> None:
    result = transpile_sql_text(
        "SELECT CAST(value AS DECIMAL(10, 2)) FROM measurements",
        "mysql",
        "postgresql",
    )

    assert result["fidelity_components"]["types"] == "EXACT"
    assert result["type_semantics"]["risk_count"] == 0
    projections = result["type_semantics"]["projections"]
    assert projections
    assert projections[0]["source_family"] == "DECIMAL"
    assert projections[0]["target_family"] == "DECIMAL"


def test_variant_to_json_is_independently_type_lossy() -> None:
    result = transpile_sql_text(
        "SELECT CAST('1' AS VARIANT) AS value",
        "snowflake",
        "postgresql",
        allow_lossy=True,
    )

    assert result["fidelity_components"]["types"] == "LOSSY"
    assert result["combined_fidelity"] == "LOSSY"
    risks = result["type_semantics"]["risks"]
    assert {risk["code"] for risk in risks} == {"VARIANT_TO_JSON_REPRESENTATION"}
    assert risks[0]["source_family"] == "VARIANT"
    assert risks[0]["target_family"] == "JSON"
