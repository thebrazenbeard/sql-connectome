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
    filter_relation = next(item for item in relations if item["kind"] == "FILTER")
    assert subquery["relation_id"] in filter_relation["inputs"]
    correlated = [
        item
        for item in result["logical_semantics"]["plan"]["expressions"]
        if item["outer_scope_id"] == "scope:select:0"
    ]
    assert correlated
    assert any(item["kind"] == "FIELD_REFERENCE" for item in correlated)


def test_unimplemented_relational_semantics_are_explicit_losses():
    result = bind_sql_text(
        "SELECT DISTINCT id FROM users ORDER BY id",
        "postgresql",
        SCHEMA,
    )
    losses = set(result["logical_semantics"]["plan"]["losses"])
    assert "DISTINCT_NOT_DERIVED_V1" in losses
    assert "SORT_NOT_DERIVED_V1" in losses


def test_set_operation_type_reconciliation_is_not_overclaimed():
    result = bind_sql_text(
        "SELECT id FROM users UNION ALL SELECT user_id AS id FROM orders",
        "postgresql",
        SCHEMA,
    )
    losses = result["logical_semantics"]["plan"]["losses"]
    assert "SET_OP_TYPE_RECONCILIATION_UNQUALIFIED_V1" in losses


def test_multiple_subqueries_get_distinct_scope_ids():
    result = bind_sql_text(
        "SELECT id FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id) "
        "AND EXISTS (SELECT 1 FROM orders o2 WHERE o2.user_id = u.id)",
        "postgresql",
        SCHEMA,
    )
    scopes = [
        item["scope_id"]
        for item in result["logical_semantics"]["plan"]["relations"]
        if item["kind"] == "SUBQUERY"
    ]
    assert scopes == ["scope:subquery:0", "scope:subquery:1"]


def test_join_and_subquery_detail_losses_are_explicit():
    result = bind_sql_text(
        "SELECT users.id FROM users JOIN orders ON users.id = orders.user_id",
        "postgresql",
        SCHEMA,
    )
    losses = set(result["logical_semantics"]["plan"]["losses"])
    assert "JOIN_PREDICATE_AND_TYPE_DETAIL_NOT_MODELED_V1" in losses
