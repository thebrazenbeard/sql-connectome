import pytest

from sql_connectome.connectome import (
    DEFAULT_CATALOG,
    SQLTextError,
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
