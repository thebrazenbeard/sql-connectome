import pytest

from sql_connectome.occurrence_envelope import (
    InMemoryReplayGuard,
    OccurrenceEnvelope,
    TrustPolicy,
    occurrence_payload_digest,
    verify_occurrence,
)


class DeterministicVerifier:
    def verify(self, *, signer_id, algorithm, payload_digest, signature):
        return (
            signer_id == "ci"
            and algorithm == "TEST"
            and signature == f"sig:{payload_digest}"
        )


def envelope(**changes):
    values = dict(
        receipt_digest="a" * 64,
        occurrence_id="run-1",
        issued_at="2026-09-28T23:30:00Z",
        nonce="nonce-1",
    )
    values.update(changes)
    return OccurrenceEnvelope(**values)


def test_occurrence_identity_is_separate_from_receipt_identity() -> None:
    first = envelope(nonce="one")
    second = envelope(nonce="two")
    assert first.receipt_digest == second.receipt_digest
    assert first.digest() != second.digest()


def test_unsigned_occurrence_allowed_only_when_policy_allows_it() -> None:
    verify_occurrence(envelope(), policy=TrustPolicy())
    with pytest.raises(ValueError, match="requires a signature"):
        verify_occurrence(envelope(), policy=TrustPolicy(require_signature=True))


def test_signed_occurrence_verifies_through_injected_trust_mechanism() -> None:
    base = envelope(signer_id="ci", signature_algorithm="TEST")
    signed = envelope(
        signer_id="ci",
        signature_algorithm="TEST",
        signature=f"sig:{occurrence_payload_digest(base)}",
    )
    verify_occurrence(
        signed,
        policy=TrustPolicy(require_signature=True, allowed_signers=("ci",)),
        verifier=DeterministicVerifier(),
    )


def test_untrusted_signer_fails_closed() -> None:
    signed = envelope(signer_id="evil", signature_algorithm="TEST", signature="x")
    with pytest.raises(ValueError, match="not trusted"):
        verify_occurrence(
            signed,
            policy=TrustPolicy(require_signature=True, allowed_signers=("ci",)),
            verifier=DeterministicVerifier(),
        )


def test_replay_guard_rejects_same_occurrence_twice() -> None:
    guard = InMemoryReplayGuard()
    item = envelope()
    verify_occurrence(item, policy=TrustPolicy(), replay_guard=guard)
    with pytest.raises(ValueError, match="replay"):
        verify_occurrence(item, policy=TrustPolicy(), replay_guard=guard)
