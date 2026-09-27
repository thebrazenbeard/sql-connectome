import os

import pytest

from sql_connectome.config import Settings
from sql_connectome.qualification import qualify_translation_to_postgresql
from sql_connectome.receipts import canonical_digest

DSN = os.getenv("SQL_CONNECTOME_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="SQL_CONNECTOME_DATABASE_URL not set")


def settings() -> Settings:
    assert DSN
    return Settings(database_url=DSN, api_token="integration-token")


def test_mysql_translation_qualifies_against_real_postgresql() -> None:
    result = qualify_translation_to_postgresql(
        settings(),
        """
        SELECT version
        FROM sql_connectome.schema_migrations
        ORDER BY version
        LIMIT 5
        """,
        "mysql",
    )

    assert result["schema"] == "SQL_CONNECTOME_TRANSLATION_QUALIFICATION_V2"
    assert result["qualification"]["status"] == "PASS"
    assert result["qualification"]["translation_fidelity"] == "EXACT"
    assert result["qualification"]["capability_fidelity"] == "EXACT"
    assert result["qualification"]["expression_semantic_fidelity"] == "EXACT"
    assert result["qualification"]["type_fidelity"] == "EXACT"
    assert result["qualification"]["translation_fidelity_scope"] == (
        "CAPABILITY_EXPRESSION_AND_TYPE_SEMANTICS"
    )
    assert result["qualification"]["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert result["qualification"]["query_executed"] is False
    assert result["engine_validation"]["validation"]["status"] == "PASS"
    assert len(result["receipt"]["receipt_digest"]) == 64
    assert result["receipt"]["subject"]["catalog_digest"] == result["translation"]["catalog_digest"]
    qualification = result["qualification"]
    assert qualification["source_ir_digest"] == canonical_digest(
        result["translation"]["source"]["ir"]
    )
    assert qualification["target_ir_digest"] == canonical_digest(
        result["translation"]["target_parse"]["ir"]
    )
    assert qualification["engine_validation_receipt_digest"] == (
        result["engine_validation"]["receipt"]["receipt_digest"]
    )
    assert result["receipt"]["subject"]["source_ir_digest"] == qualification["source_ir_digest"]
    assert result["receipt"]["subject"]["target_ir_digest"] == qualification["target_ir_digest"]
    assert result["receipt"]["subject"]["engine_validation_receipt_digest"] == (
        qualification["engine_validation_receipt_digest"]
    )


def test_bigquery_qualify_constructive_rewrite_plans_on_postgresql() -> None:
    result = qualify_translation_to_postgresql(
        settings(),
        """
        SELECT
            version,
            ROW_NUMBER() OVER (ORDER BY version) AS rn
        FROM sql_connectome.schema_migrations
        QUALIFY rn = 1
        """,
        "bigquery",
    )

    assert result["qualification"]["status"] == "PASS"
    assert result["qualification"]["translation_fidelity"] == "CONSTRUCTIVE"
    assert result["translation"]["plan"]["rewrites"][0]["rule_name"] == (
        "qualify-via-derived-table"
    )
    assert result["engine_validation"]["validation"]["status"] == "PASS"


def test_target_engine_failure_keeps_translation_and_fails_qualification() -> None:
    result = qualify_translation_to_postgresql(
        settings(),
        "SELECT missing_column FROM sql_connectome.schema_migrations",
        "mysql",
    )

    assert result["qualification"]["status"] == "FAIL"
    assert result["translation"]["validation"]["target_parse"] == "PASS"
    assert result["engine_validation"]["validation"]["status"] == "FAIL"
    assert result["engine_validation"]["error"]["sqlstate"] == "42703"


def test_expression_semantic_risk_caps_real_postgresql_qualification() -> None:
    result = qualify_translation_to_postgresql(
        settings(),
        "SELECT LEAST(1, NULL, 2)",
        "mysql",
        allow_lossy=True,
    )

    assert result["qualification"]["status"] == "PASS"
    assert result["qualification"]["capability_fidelity"] == "EXACT"
    assert result["qualification"]["translation_fidelity"] == "LOSSY"
    assert result["qualification"]["translation_fidelity_scope"] == (
        "CAPABILITY_EXPRESSION_AND_TYPE_SEMANTICS"
    )
    assert result["qualification"]["expression_semantic_fidelity"] == "LOSSY"
    assert result["qualification"]["type_fidelity"] == "EXACT"
    assert result["qualification"]["expression_semantic_risk_count"] == 1
    assert result["engine_validation"]["validation"]["status"] == "PASS"



def test_type_semantic_risk_is_bound_into_postgresql_qualification() -> None:
    result = qualify_translation_to_postgresql(
        settings(),
        "SELECT CAST('1' AS VARIANT) AS value",
        "snowflake",
        allow_lossy=True,
    )

    qualification = result["qualification"]
    assert qualification["status"] == "PASS"
    assert qualification["capability_fidelity"] == "LOSSY"
    assert qualification["expression_semantic_fidelity"] == "EXACT"
    assert qualification["type_fidelity"] == "LOSSY"
    assert qualification["translation_fidelity"] == "LOSSY"
    assert qualification["type_semantic_risk_count"] == 1
    assert result["translation"]["type_semantics"]["risks"][0]["code"] == (
        "VARIANT_TO_JSON_REPRESENTATION"
    )
    assert "VARIANT" not in result["translation"]["target_sql"].upper()
    assert "JSON" in result["translation"]["target_sql"].upper()
    assert result["engine_validation"]["validation"]["status"] == "PASS"


def test_semantic_evidence_digest_binds_translation_evidence() -> None:
    result = qualify_translation_to_postgresql(
        settings(),
        "SELECT version FROM sql_connectome.schema_migrations",
        "postgresql",
    )

    expected = canonical_digest(
        {
            "plan": result["translation"]["plan"],
            "expression_semantics": result["translation"]["expression_semantics"],
            "type_semantics": result["translation"]["type_semantics"],
            "combined_fidelity": result["translation"]["combined_fidelity"],
        }
    )
    assert result["qualification"]["semantic_evidence_digest"] == expected
    assert result["receipt"]["subject"]["semantic_evidence_digest"] == expected
