from dataclasses import replace

import pytest

from sql_connectome.connectivity import ConnectionIdentity
from sql_connectome.session_attestation import (
    ContinuityState,
    attest_session_identity,
    validate_session_attestation,
)


def identity(*, catalog="app", session_facts=(("role", "reader"),)):
    return ConnectionIdentity(
        provider="native",
        engine="postgresql",
        engine_version="17.6",
        transport_family="DBAPI",
        transport_implementation="psycopg",
        transport_version="3",
        endpoint_identity="db.example",
        catalog=catalog,
        session_facts=session_facts,
    )


def test_identical_reobservation_establishes_bounded_continuity() -> None:
    before = identity()
    result = attest_session_identity(before, identity(), mechanism="adapter-reobserve")
    assert result.continuity is ContinuityState.CONTINUOUS
    assert result.as_dict()["scope"] == "BOUNDED_OBSERVATION_ONLY"
    validate_session_attestation(result, before)


def test_catalog_switch_is_drift() -> None:
    result = attest_session_identity(identity(), identity(catalog="other"), mechanism="probe")
    assert result.continuity is ContinuityState.DRIFTED
    with pytest.raises(ValueError, match="does not bind execution identity|continuity"):
        validate_session_attestation(result, identity())


def test_session_fact_mutation_is_drift() -> None:
    result = attest_session_identity(
        identity(),
        identity(session_facts=(("role", "writer"),)),
        mechanism="probe",
    )
    assert result.continuity is ContinuityState.DRIFTED


def test_missing_reobservation_remains_unknown() -> None:
    result = attest_session_identity(identity(), None, mechanism="unavailable")
    assert result.continuity is ContinuityState.UNKNOWN
    with pytest.raises(ValueError):
        validate_session_attestation(result, identity())


def test_attestation_digest_binds_mechanism_and_evidence() -> None:
    before = identity()
    first = attest_session_identity(before, identity(), mechanism="probe", evidence_refs=("p:1",))
    other = attest_session_identity(before, identity(), mechanism="probe", evidence_refs=("p:2",))
    assert first.digest() != other.digest()


def test_claimed_continuity_must_bind_prior_identity_to_observed_identity() -> None:
    before = identity()
    real = attest_session_identity(before, before, mechanism="adapter-reobserve")
    # A serialized/foreign receipt can claim CONTINUOUS while carrying a prior
    # digest from a different session. Validation must reject this mismatch.
    mismatched = replace(
        real,
        prior_identity_digest=attest_session_identity(
            identity(catalog="other"), before, mechanism="adapter-reobserve"
        ).prior_identity_digest,
    )
    with pytest.raises(ValueError, match="prior identity|continuity"):
        validate_session_attestation(mismatched, before)
