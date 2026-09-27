import pytest

from sql_connectome.connectome import (
    DEFAULT_CATALOG,
    DEFAULT_EXPRESSION_REGISTRY,
    SQLTextError,
    type_graph_digest,
    parse_sql_text,
    transpile_sql_text,
)


def test_parse_postgresql_into_semantic_ir() -> None:
    analysis = parse_sql_text(
        "SELECT user_id, count(*) AS n FROM events GROUP BY user_id",
        "postgresql",
    )

    payload = analysis.as_dict()
    ir = payload["ir"]

    assert payload["parser"]["engine"] == "sqlglot"
    assert payload["catalog_digest"] == DEFAULT_CATALOG.digest
    assert ir["source_dialect"] == "postgresql"
    assert ir["operation"] == "SELECT"
    assert "relational_select" in ir["required_capabilities"]
    assert ir["input_relations"] == ["events"]
    assert ir["side_effects"] == []
    assert ir["nodes"]
    assert ir["roots"] == ["n0"]
    assert (
        ir["semantic_extensions"]["expression_semantic_registry_digest"]
        == DEFAULT_EXPRESSION_REGISTRY.digest
    )
    assert f"expression-registry:{DEFAULT_EXPRESSION_REGISTRY.digest}" in ir["provenance"]

    count_nodes = [node for node in ir["nodes"] if node["kind"] == "COUNT"]
    assert len(count_nodes) == 1
    count_attributes = count_nodes[0]["attributes"]
    assert count_attributes["semantic_state"] == "REGISTERED"
    assert count_attributes["semantic_id"] == "aggregate.count"
    assert count_attributes["semantic_family"] == "aggregate"


def test_parse_bigquery_qualify_extracts_analytical_capabilities() -> None:
    analysis = parse_sql_text(
        """
        SELECT
            user_id,
            ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
        FROM events
        QUALIFY rn = 1
        """,
        "bigquery",
    )

    capabilities = analysis.ir.required_capabilities

    assert "relational_select" in capabilities
    assert "window_functions" in capabilities
    assert "qualify" in capabilities
    assert analysis.ir.semantic_dimensions


def test_parse_requires_one_statement() -> None:
    with pytest.raises(SQLTextError, match="SINGLE_STATEMENT_REQUIRED"):
        parse_sql_text("SELECT 1; SELECT 2", "postgresql")


def test_parse_rejects_invalid_sql() -> None:
    with pytest.raises(SQLTextError, match="PARSE_ERROR"):
        parse_sql_text("SELECT FROM", "postgresql")


def test_transpile_simple_query_and_reparse_target() -> None:
    result = transpile_sql_text(
        "SELECT id, name FROM users WHERE active = 1",
        "mysql",
        "postgresql",
    )

    assert result["catalog_digest"] == DEFAULT_CATALOG.digest
    assert result["plan"]["fidelity"] == "EXACT"
    assert result["validation"]["source_parse"] == "PASS"
    assert result["validation"]["target_parse"] == "PASS"
    assert result["validation"]["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert result["target_parse"]["ir"]["source_dialect"] == "postgresql"
    assert result["target_sql"]


def test_lossy_translation_requires_explicit_opt_in() -> None:
    with pytest.raises(SQLTextError, match="LOSSY_TRANSLATION_REQUIRES_OPT_IN"):
        transpile_sql_text(
            "SELECT CAST('1' AS VARIANT) AS value",
            "snowflake",
            "postgresql",
        )



def test_parse_preserves_unregistered_function_identity() -> None:
    analysis = parse_sql_text(
        "SELECT mystery_function(value) FROM events",
        "postgresql",
    )

    payload = analysis.as_dict()
    nodes = payload["ir"]["nodes"]
    anonymous = [node for node in nodes if node["kind"] == "ANONYMOUS"]

    assert len(anonymous) == 1
    attributes = anonymous[0]["attributes"]
    assert attributes["semantic_state"] == "UNREGISTERED"
    assert attributes["semantic_id"] is None
    assert attributes["semantic_source_name"] == "mystery_function"



def test_parse_binds_explicit_type_semantics_into_ir() -> None:
    analysis = parse_sql_text(
        "SELECT CAST(amount AS DECIMAL(10, 2)) FROM measurements",
        "postgresql",
    )

    payload = analysis.as_dict()
    ir = payload["ir"]
    data_types = [node for node in ir["nodes"] if node["kind"] == "DATATYPE"]

    assert len(data_types) == 1
    attributes = data_types[0]["attributes"]
    assert attributes["type_semantic_state"] == "EXPLICIT"
    assert attributes["type_dialect_name"] == "DECIMAL"
    assert attributes["type_canonical_family"] == "DECIMAL"
    assert attributes["type_source_sql"] == "DECIMAL(10, 2)"
    assert attributes["type_parameters"] == ["10", "2"]
    assert attributes["type_evidence_basis"] == "PARSED_EXPLICIT_TYPE"

    expected_digest = type_graph_digest(
        dialect_id="postgresql",
        parser_dialect="postgres",
    )
    extensions = ir["semantic_extensions"]
    assert extensions["source_type_graph_schema"] == "SQL_CONNECTOME_TYPE_GRAPH_V1"
    assert extensions["source_type_graph_digest"] == expected_digest
    assert extensions["type_semantic_coverage"] == "EXPLICIT_TYPES_ONLY"
    assert f"type-graph:postgresql:{expected_digest}" in ir["provenance"]


def test_parse_preserves_variant_type_identity_in_ir() -> None:
    analysis = parse_sql_text(
        "SELECT CAST('1' AS VARIANT) AS value",
        "snowflake",
    )

    payload = analysis.as_dict()
    data_types = [
        node
        for node in payload["ir"]["nodes"]
        if node["kind"] == "DATATYPE"
    ]

    assert len(data_types) == 1
    attributes = data_types[0]["attributes"]
    assert attributes["type_dialect_name"] == "VARIANT"
    assert attributes["type_canonical_family"] == "VARIANT"
    assert attributes["type_semantic_state"] == "EXPLICIT"
