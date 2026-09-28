from sql_connectome.connectome import bind_sql_text

SCHEMA = {
    "users": {"id": "INT"},
    "orders": {"user_id": "INT"},
}


def test_union_all_and_union_preserve_multiplicity_difference():
    union_all = bind_sql_text(
        "SELECT id FROM users UNION ALL SELECT user_id AS id FROM orders",
        "postgresql",
        SCHEMA,
    )
    union_set = bind_sql_text(
        "SELECT id FROM users UNION SELECT user_id AS id FROM orders",
        "postgresql",
        SCHEMA,
    )
    all_root = union_all["logical_semantics"]["plan"]["relations"][-1]
    set_root = union_set["logical_semantics"]["plan"]["relations"][-1]
    assert all_root["kind"] == "SET_OP"
    assert all_root["multiplicity"] == "BAG"
    assert set_root["kind"] == "SET_OP"
    assert set_root["multiplicity"] == "SET"


def test_aggregate_without_group_has_maximum_one_row():
    result = bind_sql_text("SELECT COUNT(*) AS n FROM users", "postgresql", SCHEMA)
    aggregate = next(
        item
        for item in result["logical_semantics"]["plan"]["relations"]
        if item["kind"] == "AGGREGATE"
    )
    assert aggregate["cardinality"]["maximum"] == 1


def test_correlated_exists_is_not_silently_flattened():
    result = bind_sql_text(
        "SELECT id FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id)",
        "postgresql",
        SCHEMA,
    )
    relations = result["logical_semantics"]["plan"]["relations"]
    assert any(item["kind"] == "SUBQUERY" for item in relations)
    subquery = next(item for item in relations if item["kind"] == "SUBQUERY")
    assert subquery["scope_id"] != "scope:select:0"
