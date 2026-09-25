import sqlite3

import pytest

from sql_connectome.sqlite_engine import _select_authorizer, validate_sqlite_readonly
from sql_connectome.sql_guard import SQLRejected


def test_sqlite_validation_plans_against_in_memory_schema() -> None:
    result = validate_sqlite_readonly(
        "SELECT id, amount * 2 AS doubled FROM orders WHERE amount > ?",
        schema_context={
            "orders": {
                "id": "INTEGER",
                "amount": "REAL",
            }
        },
        params=[10],
    )

    assert result["validation"]["status"] == "PASS"
    assert result["validation"]["engine"] == "sqlite"
    assert result["validation"]["mode"] == "EXPLAIN_QUERY_PLAN"
    assert result["validation"]["query_executed"] is False
    assert result["validation"]["in_memory"] is True
    assert result["validation"]["extension_loading"] is False
    assert result["validation"]["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert result["runtime"]["database"] == ":memory:"
    assert result["runtime"]["query_only"] is True
    assert result["runtime"]["authorizer"] == "SELECT_READ_FUNCTION_ONLY"
    assert result["plan"]
    assert result["receipt"]["kind"] == "SQLITE_ENGINE_VALIDATION"


def test_sqlite_validation_reports_binder_failure() -> None:
    result = validate_sqlite_readonly(
        "SELECT missing_column FROM orders",
        schema_context={"orders": {"id": "INTEGER"}},
    )

    assert result["validation"]["status"] == "FAIL"
    assert result["validation"]["query_executed"] is False
    assert result["plan"] is None
    assert result["error"] is not None
    assert result["error"]["error_class"] == "OperationalError"
    assert "no such column" in result["error"]["message"].lower()


def test_sqlite_authorizer_allows_select_reads_and_denies_attach_pragma() -> None:
    assert _select_authorizer(sqlite3.SQLITE_SELECT, None, None, None, None) == sqlite3.SQLITE_OK
    assert _select_authorizer(sqlite3.SQLITE_READ, "t", "c", "main", None) == sqlite3.SQLITE_OK
    assert _select_authorizer(sqlite3.SQLITE_FUNCTION, None, "length", None, None) == sqlite3.SQLITE_OK
    assert _select_authorizer(sqlite3.SQLITE_ATTACH, "x.db", None, None, None) == sqlite3.SQLITE_DENY
    assert _select_authorizer(sqlite3.SQLITE_PRAGMA, "query_only", None, None, None) == sqlite3.SQLITE_DENY


def test_sqlite_validation_blocks_extension_loading() -> None:
    result = validate_sqlite_readonly("SELECT load_extension('not-real')")

    assert result["validation"]["status"] == "FAIL"
    assert result["validation"]["extension_loading"] is False
    assert result["validation"]["query_executed"] is False
    assert result["error"] is not None


def test_sqlite_validation_supports_recursive_select_planning() -> None:
    result = validate_sqlite_readonly(
        "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 3) "
        "SELECT x FROM n"
    )

    assert result["validation"]["status"] == "PASS"
    assert result["plan"]


def test_sqlite_validation_rejects_non_select() -> None:
    with pytest.raises(SQLRejected):
        validate_sqlite_readonly("CREATE TABLE unsafe(id INTEGER)")


def test_sqlite_validation_rejects_schema_type_statement_smuggling() -> None:
    with pytest.raises(ValueError, match="INVALID_SQLITE_TYPE"):
        validate_sqlite_readonly(
            "SELECT value FROM sample",
            schema_context={"sample": {"value": "INTEGER; DROP TABLE sample"}},
        )
