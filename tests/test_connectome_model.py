import pytest

from sql_connectome.connectome import (
    TranslationFidelity,
    list_dialects,
    plan_translation,
    resolve_dialect,
)


def test_resolves_alias_to_canonical_dialect() -> None:
    assert resolve_dialect("postgres").dialect_id == "postgresql"
    assert resolve_dialect("MSSQL").dialect_id == "tsql"


def test_unknown_dialect_fails_closed() -> None:
    with pytest.raises(KeyError, match="UNKNOWN_DIALECT"):
        resolve_dialect("made-up-sql")


def test_native_capabilities_are_exact() -> None:
    plan = plan_translation(
        "bigquery",
        "duckdb",
        {"relational_select", "window_functions", "qualify"},
    )

    assert plan.fidelity is TranslationFidelity.EXACT
    assert plan.missing_capabilities == frozenset()
    assert plan.rewrites == ()


def test_qualify_can_be_constructively_rewritten_for_postgresql() -> None:
    plan = plan_translation(
        "bigquery",
        "postgresql",
        {"relational_select", "window_functions", "qualify"},
    )

    assert plan.fidelity is TranslationFidelity.CONSTRUCTIVE
    assert plan.missing_capabilities == frozenset({"qualify"})
    assert plan.unresolved_capabilities == frozenset()
    assert plan.rewrites[0].rule_name == "qualify-via-derived-table"


def test_oracle_connect_by_is_not_overclaimed_as_exact() -> None:
    plan = plan_translation(
        "oracle",
        "postgresql",
        {"relational_select", "connect_by"},
    )

    assert plan.fidelity is TranslationFidelity.LOSSY
    assert plan.rewrites[0].rule_name == "connect-by-via-recursive-cte"


def test_unresolved_capability_is_unrepresentable() -> None:
    plan = plan_translation(
        "snowflake",
        "sqlite",
        {"relational_select", "geospatial"},
    )

    assert plan.fidelity is TranslationFidelity.UNREPRESENTABLE
    assert plan.unresolved_capabilities == frozenset({"geospatial"})


def test_dialect_inventory_is_deterministic() -> None:
    dialects = list_dialects()
    ids = [item["dialect_id"] for item in dialects]

    assert ids == sorted(ids)
    assert "postgresql" in ids
    assert "oracle" in ids
    assert "bigquery" in ids
