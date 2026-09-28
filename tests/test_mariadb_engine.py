import pytest

from sql_connectome.mariadb_engine import validate_mariadb_readonly
from sql_connectome.sql_guard import SQLRejected


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.current = ""

    def execute(self, sql: str) -> None:
        self.current = sql
        self.calls.append(sql)

    def fetchone(self):
        if self.current.startswith("SELECT VERSION"):
            return ("11.8.0", "app", "STRICT_TRANS_TABLES", "utf8mb4_0900_ai_ci", "+00:00", "2")
        if self.current.startswith("EXPLAIN FORMAT=JSON"):
            return ('{"query_block":{"select_id":1}}',)
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_value = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.cursor_value


def test_mariadb_validation_is_nonexecuting_and_identity_bound() -> None:
    connection = FakeConnection()
    result = validate_mariadb_readonly(
        "SELECT id FROM orders",
        connection=connection,
        schema_context={"orders": {"id": "INTEGER"}},
    )
    assert result.status.value == "PASS"
    assert result.runtime.engine == "mariadb"
    assert result.runtime.adapter_id == "mariadb-v1"
    assert dict(result.runtime.facts)["database"] == "app"
    assert result.query_executed is False
    assert any(call.startswith("EXPLAIN FORMAT=JSON") for call in connection.cursor_value.calls)
    assert not any("ANALYZE" in call.upper() for call in connection.cursor_value.calls)
    assert not any(
        call.upper().startswith(("CREATE ", "ALTER ", "DROP "))
        for call in connection.cursor_value.calls
    )


def test_mariadb_unavailable_and_guarded() -> None:
    assert validate_mariadb_readonly("SELECT 1", connection=None).status.value == "UNAVAILABLE"
    with pytest.raises(SQLRejected):
        validate_mariadb_readonly("DELETE FROM orders", connection=FakeConnection())
