import pytest

from sql_connectome.sql_guard import SQLRejected
from sql_connectome.trino_engine import validate_trino_readonly


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.current = ""

    def execute(self, sql: str) -> None:
        self.current = sql
        self.calls.append(sql)

    def fetchone(self):
        if self.current.startswith("SELECT version"):
            return ("477", "hive", "analytics")
        if self.current.startswith("EXPLAIN (TYPE VALIDATE)"):
            return (True,)
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_value = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.cursor_value


def test_trino_uses_validate_explain_without_execution() -> None:
    connection = FakeConnection()
    result = validate_trino_readonly(
        "SELECT id FROM orders",
        connection=connection,
        schema_context={"orders": {"id": "BIGINT"}},
    )
    assert result.status.value == "PASS"
    assert result.runtime.engine == "trino"
    assert dict(result.runtime.facts)["catalog"] == "hive"
    assert dict(result.runtime.facts)["schema"] == "analytics"
    assert result.query_executed is False
    assert "EXPLAIN (TYPE VALIDATE) SELECT id FROM orders" in connection.cursor_value.calls
    assert not any("ANALYZE" in call.upper() for call in connection.cursor_value.calls)


def test_trino_unavailable_and_guarded() -> None:
    assert validate_trino_readonly("SELECT 1", connection=None).status.value == "UNAVAILABLE"
    with pytest.raises(SQLRejected):
        validate_trino_readonly("DROP TABLE orders", connection=FakeConnection())
