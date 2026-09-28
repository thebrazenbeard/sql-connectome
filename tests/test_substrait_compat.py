from sql_connectome.connectome import bind_sql_text
from sql_connectome.connectome.substrait_compat import (
    CompatibilityState,
    inspect_substrait_compatibility,
)

SCHEMA = {"users": {"id": "INT"}}


def test_core_logical_plan_has_exact_substrait_relational_mapping():
    result = bind_sql_text("SELECT id FROM users LIMIT 2", "postgresql", SCHEMA)
    compatibility = inspect_substrait_compatibility(result["logical_semantics"]["plan"])
    assert compatibility.overall is CompatibilityState.EXACT
    assert compatibility.authority == "INTEROPERABILITY_INSPECTION_ONLY"


def test_unknown_type_does_not_become_exact():
    result = bind_sql_text(
        "SELECT mystery_function(id) AS mystery FROM users",
        "postgresql",
        SCHEMA,
    )
    compatibility = inspect_substrait_compatibility(result["logical_semantics"]["plan"])
    assert compatibility.overall is CompatibilityState.UNKNOWN
