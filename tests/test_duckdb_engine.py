import pytest

from sql_connectome.duckdb_engine import validate_duckdb_readonly
from sql_connectome.sql_guard import SQLRejected


def test_duckdb_validation_plans_against_in_memory_schema() -> None:
    result = validate_duckdb_readonly(
        "SELECT id, amount * 2 AS doubled FROM orders WHERE amount > ?",
        schema_context={
            "orders": {
                "id": "INTEGER",
                "amount": "DOUBLE",
            }
        },
        params=[10],
    )

    assert result["validation"]["status"] == "PASS"
    assert result["validation"]["engine"] == "duckdb"
    assert result["validation"]["mode"] == "EXPLAIN"
    assert result["validation"]["query_executed"] is False
    assert result["validation"]["in_memory"] is True
    assert result["validation"]["external_access"] is False
    assert result["validation"]["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert result["runtime"]["database"] == ":memory:"
    assert result["runtime"]["enable_external_access"] is False
    assert result["runtime"]["allow_community_extensions"] is False
    assert result["runtime"]["allow_unsigned_extensions"] is False
    assert result["runtime"]["autoinstall_known_extensions"] is False
    assert result["runtime"]["autoload_known_extensions"] is False
    assert result["runtime"]["lock_configuration"] is True
    assert result["plan"]
    assert result["receipt"]["kind"] == "DUCKDB_ENGINE_VALIDATION"


def test_duckdb_validation_reports_binder_failure() -> None:
    result = validate_duckdb_readonly(
        "SELECT missing_column FROM orders",
        schema_context={"orders": {"id": "INTEGER"}},
    )

    assert result["validation"]["status"] == "FAIL"
    assert result["validation"]["query_executed"] is False
    assert result["plan"] is None
    assert result["error"] is not None
    assert "Binder" in result["error"]["error_class"]


def test_duckdb_validation_blocks_external_file_access() -> None:
    result = validate_duckdb_readonly(
        "SELECT * FROM read_csv_auto('/etc/passwd')",
    )

    assert result["validation"]["status"] == "FAIL"
    assert result["validation"]["external_access"] is False
    assert result["validation"]["query_executed"] is False
    assert result["error"] is not None
    message = result["error"]["message"].lower()
    assert "external" in message or "disabled" in message


def test_duckdb_validation_rejects_non_select() -> None:
    with pytest.raises(SQLRejected):
        validate_duckdb_readonly("CREATE TABLE unsafe(id INTEGER)")


def test_duckdb_validation_rejects_schema_type_statement_smuggling() -> None:
    with pytest.raises(ValueError, match="INVALID_DUCKDB_TYPE"):
        validate_duckdb_readonly(
            "SELECT value FROM sample",
            schema_context={"sample": {"value": "INTEGER; DROP TABLE sample"}},
        )


def test_duckdb_validation_normalizes_unknown_schema_type_failure() -> None:
    with pytest.raises(ValueError, match="INVALID_DUCKDB_SCHEMA"):
        validate_duckdb_readonly(
            "SELECT value FROM sample",
            schema_context={"sample": {"value": "NOT_A_REAL_DUCKDB_TYPE"}},
        )
