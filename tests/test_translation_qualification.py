import os

import pytest

from sql_connectome.config import Settings
from sql_connectome.qualification import qualify_translation_to_postgresql

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

    assert result["qualification"]["status"] == "PASS"
    assert result["qualification"]["translation_fidelity"] == "EXACT"
    assert result["qualification"]["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert result["qualification"]["query_executed"] is False
    assert result["engine_validation"]["validation"]["status"] == "PASS"
    assert len(result["receipt"]["receipt_digest"]) == 64


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
