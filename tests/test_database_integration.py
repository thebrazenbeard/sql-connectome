import os

import psycopg
import pytest

from sql_connectome.config import Settings
from sql_connectome.db import (
    migration_status,
    platform_health,
    query_readonly,
    schema_inventory,
    validate_postgresql_readonly,
)
from sql_connectome.sql_guard import SQLRejected

DSN = os.getenv("SQL_CONNECTOME_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DSN, reason="SQL_CONNECTOME_DATABASE_URL not set")


def settings() -> Settings:
    assert DSN
    return Settings(database_url=DSN, api_token="integration-token")


def test_platform_and_migration_identity() -> None:
    health = platform_health(settings())
    assert health["status"] == "ok"
    assert health["runtime"]["server_version_num"]
    assert len(health["runtime"]["identity_digest"]) == 64

    migrations = migration_status(settings())
    assert migrations["applied"]
    assert migrations["applied"][0]["version"] == "0001"


def test_schema_inventory_contains_control_schema() -> None:
    inventory = schema_inventory(settings())
    names = {(row["table_schema"], row["table_name"]) for row in inventory["tables"]}
    assert ("sql_connectome", "schema_migrations") in names
    assert ("sql_connectome", "effect_receipts") in names


def test_readonly_query_roundtrip() -> None:
    result = query_readonly(settings(), "SELECT 1 AS one")
    assert result["rows"] == [{"one": 1}]
    assert result["truncated"] is False


def test_readonly_transaction_blocks_write_cte() -> None:
    s = settings()
    smuggled = (
        "WITH doomed AS ("
        "DELETE FROM sql_connectome.platform_metadata RETURNING platform_schema"
        ") SELECT * FROM doomed"
    )

    with pytest.raises((psycopg.errors.ReadOnlySqlTransaction, SQLRejected)):
        query_readonly(s, smuggled)

    with psycopg.connect(s.database_url) as conn:
        count = conn.execute(
            "SELECT count(*) FROM sql_connectome.platform_metadata"
        ).fetchone()[0]
    assert count == 1


def test_postgres_engine_validation_passes_real_plan() -> None:
    result = validate_postgresql_readonly(
        settings(),
        "SELECT version FROM sql_connectome.schema_migrations ORDER BY version",
    )

    assert result["validation"]["status"] == "PASS"
    assert result["validation"]["query_executed"] is False
    assert result["validation"]["read_only_transaction"] is True
    assert result["plan"]
    assert result["error"] is None


def test_postgres_engine_validation_returns_binding_failure() -> None:
    result = validate_postgresql_readonly(
        settings(),
        "SELECT definitely_missing FROM sql_connectome.schema_migrations",
    )

    assert result["validation"]["status"] == "FAIL"
    assert result["plan"] is None
    assert result["error"]["sqlstate"] == "42703"


def test_postgres_engine_validation_rejects_non_select() -> None:
    with pytest.raises(SQLRejected, match="ONLY_SELECT_ALLOWED"):
        validate_postgresql_readonly(
            settings(),
            "UPDATE sql_connectome.platform_metadata SET platform_schema = 'bad'",
        )
