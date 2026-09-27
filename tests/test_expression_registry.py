from sql_connectome.connectome import (
    DEFAULT_EXPRESSION_REGISTRY,
    inspect_expression_registry,
)


def _bindings_by_class(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    bindings = payload["bindings"]
    assert isinstance(bindings, list)
    return {str(row["expression_class"]): row for row in bindings}


def test_registry_manifest_is_stable_and_source_controlled() -> None:
    manifest = DEFAULT_EXPRESSION_REGISTRY.manifest()

    assert manifest["schema"] == "SQL_CONNECTOME_EXPRESSION_SEMANTIC_REGISTRY_V1"
    assert manifest["evidence_basis"] == "SOURCE_CONTROLLED_SEMANTIC_REGISTRY"
    assert manifest["evidence_ceiling"] == "DECLARED_SEMANTIC_IDENTITY"
    assert manifest["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert len(DEFAULT_EXPRESSION_REGISTRY.digest) == 64

    ids = {row["semantic_id"] for row in manifest["entries"]}
    assert "function.coalesce" in ids
    assert "operator.div" in ids
    assert "aggregate.count" in ids


def test_query_inventory_maps_known_expressions_to_stable_ids() -> None:
    payload = inspect_expression_registry(
        "SELECT COALESCE(a, b), 5 / 2, COUNT(*) FROM events",
        "postgresql",
    )
    bindings = _bindings_by_class(payload)

    assert payload["schema"] == "SQL_CONNECTOME_EXPRESSION_SEMANTIC_INVENTORY_V1"
    assert len(payload["catalog_digest"]) == 64
    assert payload["semantic_registry_digest"] == DEFAULT_EXPRESSION_REGISTRY.digest

    assert bindings["Coalesce"]["semantic_id"] == "function.coalesce"
    assert bindings["Div"]["semantic_id"] == "operator.div"
    assert bindings["Count"]["semantic_id"] == "aggregate.count"
    assert "DIVISION_TYPE_SEMANTICS" in bindings["Div"]["known_risk_codes"]


def test_unknown_function_remains_explicitly_unregistered() -> None:
    payload = inspect_expression_registry(
        "SELECT mystery_function(value) FROM events",
        "postgresql",
    )

    unregistered = [
        row for row in payload["bindings"] if row["state"] == "UNREGISTERED"
    ]
    assert unregistered
    assert any(row["name"] == "MYSTERY_FUNCTION" for row in unregistered)
    assert all(row["semantic_id"] is None for row in unregistered)
    assert payload["unregistered_expression_classes"] >= 1


def test_registry_links_existing_null_semantic_risk() -> None:
    payload = inspect_expression_registry(
        "SELECT LEAST(a, b) FROM measurements",
        "mysql",
    )
    bindings = _bindings_by_class(payload)

    assert bindings["Least"]["semantic_id"] == "function.least"
    assert bindings["Least"]["known_risk_codes"] == [
        "LEAST_GREATEST_NULL_SEMANTICS"
    ]
