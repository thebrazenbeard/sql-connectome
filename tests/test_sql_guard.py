import pytest

from sql_connectome.sql_guard import SQLRejected, validate_readonly_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT * FROM pg_catalog.pg_tables LIMIT 1",
        "WITH x AS (SELECT 1 AS n) SELECT n FROM x",
    ],
)
def test_allows_single_select(sql: str) -> None:
    assert validate_readonly_sql(sql) == sql


@pytest.mark.parametrize(
    ("sql", "reason"),
    [
        ("", "EMPTY_SQL"),
        ("UPDATE x SET y = 1", "ONLY_SELECT_ALLOWED"),
        ("DELETE FROM x", "ONLY_SELECT_ALLOWED"),
        ("CREATE TABLE x(y int)", "ONLY_SELECT_ALLOWED"),
        ("SELECT 1; SELECT 2", "MULTI_STATEMENT"),
    ],
)
def test_rejects_non_read_shapes(sql: str, reason: str) -> None:
    with pytest.raises(SQLRejected, match=reason):
        validate_readonly_sql(sql)
