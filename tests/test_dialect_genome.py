import pytest

from sql_connectome.dialect_acquisition import (
    dependency_metadata_observation,
    engine_probe_observation,
    official_documentation_observation,
)
from sql_connectome.dialect_genome import (
    DialectGenome,
    EvidenceCurrentness,
    ReconciliationState,
    reconcile_claim,
)


def _obs(factory, value="true", currentness=EvidenceCurrentness.CURRENT, version="17"):
    return factory(
        dialect="postgresql",
        claim_key="feature.returning",
        observed_value=value,
        source_locator="source",
        source_digest="sha256:source",
        source_version=version,
        engine_version=version,
        acquired_at="2026-09-28T00:00:00Z",
        currentness=currentness,
    )


def test_observation_digest_binds_evidence_class_and_value() -> None:
    doc = _obs(official_documentation_observation)
    probe = _obs(engine_probe_observation)
    false_doc = _obs(official_documentation_observation, value="false")
    assert doc.digest() != probe.digest()
    assert doc.digest() != false_doc.digest()


def test_reconciliation_preserves_conflict_and_all_observations() -> None:
    doc = _obs(official_documentation_observation, value="true")
    probe = _obs(engine_probe_observation, value="false")
    result = reconcile_claim((doc, probe))
    assert result.state is ReconciliationState.CONFLICTS
    assert result.observation_digests == (doc.digest(), probe.digest())


def test_single_evidence_class_is_insufficient() -> None:
    result = reconcile_claim((_obs(official_documentation_observation),))
    assert result.state is ReconciliationState.INSUFFICIENT


def test_multiple_independent_classes_can_agree_without_becoming_truth() -> None:
    doc = _obs(official_documentation_observation)
    probe = _obs(engine_probe_observation)
    metadata = _obs(dependency_metadata_observation)
    result = reconcile_claim((doc, probe, metadata))
    assert result.state is ReconciliationState.AGREES
    assert "same value" in result.reason


def test_only_stale_or_version_mismatched_evidence_is_stale() -> None:
    stale = _obs(official_documentation_observation, currentness=EvidenceCurrentness.STALE)
    mismatch = _obs(engine_probe_observation, currentness=EvidenceCurrentness.VERSION_MISMATCH)
    assert reconcile_claim((stale, mismatch)).state is ReconciliationState.STALE


def test_genome_rejects_cross_dialect_observation() -> None:
    pg = _obs(official_documentation_observation)
    mysql = official_documentation_observation(
        dialect="mysql",
        claim_key=pg.claim_key,
        observed_value="true",
        source_locator="source",
        source_digest="digest",
        currentness=EvidenceCurrentness.UNKNOWN,
    )
    with pytest.raises(ValueError):
        DialectGenome("postgresql", "17", "v1", (pg, mysql), ())


def test_genome_digest_is_deterministic_and_version_relative() -> None:
    doc = _obs(official_documentation_observation)
    probe = _obs(engine_probe_observation)
    reconciliation = reconcile_claim((doc, probe))
    first = DialectGenome("postgresql", "17", "v1", (doc, probe), (reconciliation,))
    same = DialectGenome("postgresql", "17", "v1", (doc, probe), (reconciliation,))
    other = DialectGenome("postgresql", "16", "v1", (doc, probe), (reconciliation,))
    assert first.digest() == same.digest()
    assert first.digest() != other.digest()
