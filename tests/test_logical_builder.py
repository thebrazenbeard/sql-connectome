from sql_connectome.connectome import bind_sql_text

SCHEMA = {"users": {"id": "INT", "name": "TEXT", "active": "BOOLEAN"}}


def test_binding_emits_read_filter_project_logical_plan():
    result = bind_sql_text(
        "SELECT id, name FROM users WHERE active = TRUE",
        "postgresql",
        SCHEMA,
    )
    logical = result["logical_semantics"]
    assert logical["schema"] == "SQL_CONNECTOME_LOGICAL_SEMANTICS_V1"
    kinds = [item["kind"] for item in logical["plan"]["relations"]]
    assert kinds == ["READ", "FILTER", "PROJECT"]
    assert logical["authority"] == "STATIC_ANALYSIS_ONLY"
    assert logical["behavioral_equivalence"] == "NOT_ESTABLISHED"


def test_limit_tightens_semantic_cardinality_bound():
    result = bind_sql_text("SELECT id FROM users LIMIT 5", "postgresql", SCHEMA)
    relations = result["logical_semantics"]["plan"]["relations"]
    limit = next(item for item in relations if item["kind"] == "LIMIT")
    assert limit["cardinality"]["maximum"] == 5
    assert limit["cardinality"]["certainty"] == "DERIVED"


def test_left_join_null_extends_right_output():
    schema = {
        "users": {"id": "INT"},
        "orders": {"user_id": "INT", "total": "DECIMAL"},
    }
    result = bind_sql_text(
        "SELECT users.id, orders.total FROM users LEFT JOIN orders ON users.id = orders.user_id",
        "postgresql",
        schema,
    )
    project = next(
        item
        for item in result["logical_semantics"]["plan"]["relations"]
        if item["kind"] == "PROJECT"
    )
    fields = {field["name"]: field for field in project["output_schema"]}
    assert fields["total"]["nullability"] == "NULLABLE"
