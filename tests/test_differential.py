import pytest

from sql_connectome.differential import (
    DifferentialProbe,
    run_differential_conformance,
)


ADDITION = DifferentialProbe(
    probe_id="test_integer_addition",
    sql="SELECT 1 + 2 AS value",
    purpose="Portable arithmetic baseline for tests.",
)

DIVISION = DifferentialProbe(
    probe_id="test_integer_division",
    sql="SELECT 5 / 2 AS value",
    purpose="Known DuckDB/SQLite integer-division divergence.",
)


def _results_by_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    results = payload["results"]
    assert isinstance(results, list)
    return {
        str(result["probe"]["probe_id"]): result
        for result in results
    }


def test_embedded_differential_conformance_records_agreement_and_divergence() -> None:
    payload = run_differential_conformance(
        probes=(ADDITION, DIVISION),
        source_commit="test-commit",
    )

    assert payload["schema"] == "SQL_CONNECTOME_DIFFERENTIAL_CONFORMANCE_V1"
    assert payload["source_commit"] == "test-commit"
    assert payload["postgresql_included"] is False
    assert payload["corpus_origin"] == "BOUNDED_LIBRARY_INPUT"
    assert payload["evidence_scope"] == "BOUNDED_PROBE_SET_ONLY"
    assert payload["generalization"] == "NOT_ESTABLISHED"
    assert payload["behavioral_equivalence"] == "NOT_ESTABLISHED"

    by_id = _results_by_id(payload)

    addition = by_id["test_integer_addition"]
    assert addition["execution_outcome"] == "ALL_PASS"
    assert addition["value_outcome"] == "AGREE"
    assert addition["type_outcome"] == "AGREE"
    assert addition["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert addition["engines"][2]["status"] == "NOT_RUN"

    division = by_id["test_integer_division"]
    assert division["execution_outcome"] == "ALL_PASS"
    assert division["value_outcome"] == "DIVERGE"
    assert division["type_outcome"] == "DIVERGE"


def test_differential_receipt_binds_corpus_and_results() -> None:
    payload = run_differential_conformance(
        probes=(ADDITION,),
        source_commit="receipt-test",
    )

    receipt = payload["receipt"]
    assert receipt["kind"] == "DIFFERENTIAL_CONFORMANCE"
    subject = receipt["subject"]
    assert subject["source_commit"] == "receipt-test"
    assert len(subject["corpus_digest"]) == 64
    assert len(subject["result_digest"]) == 64
    assert subject["probe_count"] == 1


def test_differential_conformance_rejects_empty_corpus() -> None:
    with pytest.raises(ValueError, match="DIFFERENTIAL_PROBE_CORPUS_EMPTY"):
        run_differential_conformance(probes=())


def test_differential_conformance_rejects_duplicate_probe_ids() -> None:
    with pytest.raises(ValueError, match="DIFFERENTIAL_PROBE_ID_DUPLICATE"):
        run_differential_conformance(probes=(ADDITION, ADDITION))


def test_default_corpus_is_source_controlled_and_bounded() -> None:
    payload = run_differential_conformance(source_commit="default-corpus-test")

    assert payload["corpus_origin"] == "DEFAULT_SOURCE_CONTROLLED"
    assert payload["evidence_scope"] == "FIXED_SOURCE_CONTROLLED_PROBES_ONLY"
    assert payload["probe_count"] >= 6
    assert payload["postgresql_included"] is False
    assert all(
        result["behavioral_equivalence"] == "NOT_ESTABLISHED"
        for result in payload["results"]
    )
