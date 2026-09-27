import pytest

from sql_connectome.connectome import DEFAULT_CATALOG, SQLTextError, bind_sql_text

SCHEMA = {
    "users": {
        "id": "INT",
        "name": "TEXT",
        "active": "BOOLEAN",
    }
}


def test_bind_qualifies_columns_and_records_schema_digest() -> None:
    result = bind_sql_text(
        "SELECT id, name FROM users WHERE active = TRUE",
        "postgresql",
        SCHEMA,
    )

    assert result["schema"] == "SQL_CONNECTOME_STATIC_BINDING_V1"
    assert result["dialect"] == "postgresql"
    assert result["catalog_digest"] == DEFAULT_CATALOG.digest
    assert len(result["schema_digest"]) == 64
    assert result["binding"]["status"] == "STATIC_BOUND"
    assert result["binding"]["engine_validation"] == "NOT_RUN"
    assert result["binding"]["behavioral_equivalence"] == "NOT_ESTABLISHED"

    names = {(column["table"], column["name"]) for column in result["columns"]}
    assert ("users", "id") in names
    assert ("users", "name") in names
    assert ("users", "active") in names


def test_bind_expands_star_from_schema() -> None:
    result = bind_sql_text("SELECT * FROM users", "postgresql", SCHEMA)

    projection_names = {projection["name"] for projection in result["projections"]}
    assert {"id", "name", "active"}.issubset(projection_names)
    assert "*" not in result["qualified_sql"]


def test_bind_rejects_unknown_column() -> None:
    with pytest.raises(SQLTextError, match="STATIC_BIND_ERROR"):
        bind_sql_text("SELECT missing FROM users", "postgresql", SCHEMA)


def test_bind_requires_schema_context() -> None:
    with pytest.raises(SQLTextError, match="EMPTY_SCHEMA_CONTEXT"):
        bind_sql_text("SELECT 1", "postgresql", {})
