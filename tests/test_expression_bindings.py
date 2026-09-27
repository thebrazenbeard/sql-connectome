import pytest

from sql_connectome.connectome import (
    DEFAULT_CATALOG,
    DEFAULT_EXPRESSION_BINDING_PROBES,
    ExpressionBindingProbe,
    ExpressionBindingProbeSet,
    inspect_expression_bindings,
)

KNOWN_STATES = {
    "ROUNDTRIP_BOUND",
    "PARSE_FAILED",
    "PARSED_WITHOUT_EXPECTED_CLASS",
    "PARSE_BOUND_RENDER_FAILED",
    "RENDER_REPARSE_FAILED",
    "RENDERED_WITHOUT_EXPECTED_CLASS",
}


def _results_by_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    results = payload["results"]
    assert isinstance(results, list)
    return {str(row["semantic_id"]): row for row in results}


def test_probe_set_is_source_controlled_and_cross_bound() -> None:
    manifest = DEFAULT_EXPRESSION_BINDING_PROBES.manifest()

    assert manifest["schema"] == "SQL_CONNECTOME_EXPRESSION_BINDING_PROBE_SET_V1"
    assert manifest["evidence_scope"] == "SOURCE_CONTROLLED_PROBES_ONLY"
    assert len(DEFAULT_EXPRESSION_BINDING_PROBES.digest) == 64
    assert len(DEFAULT_EXPRESSION_BINDING_PROBES.probes) >= 20

    semantic_ids = {probe.semantic_id for probe in DEFAULT_EXPRESSION_BINDING_PROBES.probes}
    assert "function.coalesce" in semantic_ids
    assert "aggregate.count" in semantic_ids
    assert "operator.div" in semantic_ids
    assert "conversion.cast" in semantic_ids


def test_postgresql_binding_probe_reports_bounded_dependency_evidence() -> None:
    payload = inspect_expression_bindings("postgresql")

    assert payload["schema"] == "SQL_CONNECTOME_EXPRESSION_DIALECT_BINDINGS_V1"
    assert payload["dialect_id"] == "postgresql"
    assert payload["parser_dialect"] == "postgres"
    assert payload["catalog_digest"] == DEFAULT_CATALOG.digest
    assert payload["probe_set_digest"] == DEFAULT_EXPRESSION_BINDING_PROBES.digest
    assert payload["probe_count"] == len(DEFAULT_EXPRESSION_BINDING_PROBES.probes)
    assert payload["evidence_basis"] == "SQLGLOT_PARSER_GENERATOR_PROBES"
    assert payload["evidence_scope"] == "SOURCE_CONTROLLED_PROBES_ONLY"
    assert payload["evidence_ceiling"] == "DEPENDENCY_BEHAVIOR"
    assert payload["generalization"] == "NOT_ESTABLISHED"
    assert payload["behavioral_equivalence"] == "NOT_ESTABLISHED"

    assert sum(payload["state_counts"].values()) == payload["probe_count"]
    assert set(payload["state_counts"]).issubset(KNOWN_STATES)
    assert set(payload["roundtrip_bound_semantic_ids"]).issubset(
        {probe.semantic_id for probe in DEFAULT_EXPRESSION_BINDING_PROBES.probes}
    )


def test_basic_postgresql_semantics_roundtrip_through_parser_generator() -> None:
    payload = inspect_expression_bindings("postgresql")
    by_id = _results_by_id(payload)

    for semantic_id in (
        "function.coalesce",
        "aggregate.count",
        "operator.add",
        "conversion.cast",
    ):
        assert by_id[semantic_id]["state"] == "ROUNDTRIP_BOUND"
        assert by_id[semantic_id]["rendered_sql"]


def test_probe_set_rejects_semantic_class_mismatch() -> None:
    with pytest.raises(ValueError, match="EXPRESSION_BINDING_PROBE_CLASS_MISMATCH"):
        ExpressionBindingProbeSet(
            probes=(
                ExpressionBindingProbe(
                    semantic_id="operator.div",
                    expected_expression_class="Add",
                    sql="SELECT 5 / 2",
                    purpose="Invalid cross-binding for regression coverage.",
                ),
            )
        )
