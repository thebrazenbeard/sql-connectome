import pytest

from sql_connectome.connectome import DEFAULT_CATALOG, SQLTextError, bind_sql_text
from sql_connectome.receipts import canonical_digest

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
    assert result["binding"]["type_annotation_scope"] == "COLUMNS_AND_PROJECTIONS"
    assert result["binding"]["unknown_type_count"] == 0
    assert result["binding"]["unknown_column_type_count"] == 0
    assert result["binding"]["unknown_projection_type_count"] == 0
    assert result["binding"]["unknown_binding_type_count"] == 0

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



def test_bind_emits_separate_bound_semantic_ir() -> None:
    result = bind_sql_text(
        "SELECT id, name FROM users WHERE active = TRUE",
        "postgresql",
        SCHEMA,
    )

    bound = result["bound_semantics"]
    assert bound["schema"] == "SQL_CONNECTOME_BOUND_SEMANTICS_V1"
    assert bound["schema_digest"] == result["schema_digest"]
    assert bound["source_ir_digest"] == canonical_digest(result["source"]["ir"])
    assert bound["bound_ir_digest"] == canonical_digest(bound["ir"])
    assert bound["source_ir_digest"] != bound["bound_ir_digest"]
    assert bound["coverage"] == "QUALIFIED_IDENTIFIERS_AND_STATIC_TYPES"
    assert bound["authority"] == "STATIC_ANALYSIS_ONLY"
    assert bound["engine_validation"] == "NOT_RUN"
    assert bound["behavioral_equivalence"] == "NOT_ESTABLISHED"

    extensions = bound["ir"]["semantic_extensions"]
    assert extensions["binding_schema"] == "SQL_CONNECTOME_BOUND_SEMANTICS_V1"
    assert extensions["binding_schema_digest"] == result["schema_digest"]
    assert extensions["binding_source_ir_digest"] == bound["source_ir_digest"]
    assert extensions["binding_state"] == "STATIC_BOUND"
    assert extensions["binding_type_annotation"] == "ANNOTATED"

    column_nodes = [
        node
        for node in bound["ir"]["nodes"]
        if node["kind"] == "COLUMN"
    ]
    assert column_nodes
    by_name = {
        node["attributes"]["binding_column_name"]: node["attributes"]
        for node in column_nodes
    }
    assert by_name["id"]["binding_table_name"] == "users"
    assert by_name["id"]["binding_type_state"] == "ANNOTATED"
    assert by_name["id"]["binding_type_canonical_family"] == "INTEGER"
    assert by_name["name"]["binding_type_canonical_family"] == "STRING"
    assert by_name["active"]["binding_type_canonical_family"] == "BOOLEAN"

    source_nodes = result["source"]["ir"]["nodes"]
    assert all(
        "binding_type_state" not in node["attributes"]
        for node in source_nodes
    )


def test_bind_marks_unknown_projection_type_as_partial() -> None:
    result = bind_sql_text(
        "SELECT mystery_function(id) AS mystery FROM users",
        "postgresql",
        SCHEMA,
    )

    assert result["binding"]["type_annotation"] == "PARTIAL"
    assert result["binding"]["unknown_type_count"] == 0
    assert result["binding"]["unknown_column_type_count"] == 0
    assert result["binding"]["unknown_projection_type_count"] == 1
    assert result["binding"]["unknown_binding_type_count"] == 1

    projection = result["projections"][0]
    assert projection["name"] == "mystery"
    assert projection["unknown_type"] is True


def test_bound_ir_reflects_star_expansion_without_mutating_source_ir() -> None:
    result = bind_sql_text("SELECT * FROM users", "postgresql", SCHEMA)

    source_kinds = {node["kind"] for node in result["source"]["ir"]["nodes"]}
    bound_kinds = {
        node["kind"] for node in result["bound_semantics"]["ir"]["nodes"]
    }

    assert "STAR" in source_kinds
    assert "STAR" not in bound_kinds
    assert {"id", "name", "active"}.issubset(
        set(result["bound_semantics"]["ir"]["output_fields"])
    )
