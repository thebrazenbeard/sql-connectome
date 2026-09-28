from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .connectivity import ConnectionIdentity, connection_identity_digest
from .receipts import canonical_digest


class ContinuityState(StrEnum):
    CONTINUOUS = "CONTINUOUS"
    DRIFTED = "DRIFTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SessionAttestation:
    prior_identity_digest: str
    observed_identity_digest: str
    observed_identity: tuple[tuple[str, Any], ...]
    mechanism: str
    evidence_refs: tuple[str, ...]
    continuity: ContinuityState

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_SESSION_ATTESTATION_V1",
            "prior_identity_digest": self.prior_identity_digest,
            "observed_identity_digest": self.observed_identity_digest,
            "observed_identity": dict(self.observed_identity),
            "mechanism": self.mechanism,
            "evidence_refs": list(self.evidence_refs),
            "continuity": self.continuity.value,
            "scope": "BOUNDED_OBSERVATION_ONLY",
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


def attest_session_identity(
    prior: ConnectionIdentity,
    observed: ConnectionIdentity | None,
    *,
    mechanism: str,
    evidence_refs: tuple[str, ...] = (),
) -> SessionAttestation:
    prior_digest = connection_identity_digest(prior)
    if observed is None:
        return SessionAttestation(
            prior_digest,
            "",
            (),
            mechanism,
            evidence_refs,
            ContinuityState.UNKNOWN,
        )
    observed_digest = connection_identity_digest(observed)
    continuity = (
        ContinuityState.CONTINUOUS
        if prior_digest == observed_digest
        else ContinuityState.DRIFTED
    )
    return SessionAttestation(
        prior_digest,
        observed_digest,
        tuple(observed.as_dict().items()),
        mechanism,
        evidence_refs,
        continuity,
    )


def validate_session_attestation(
    attestation: SessionAttestation,
    identity: ConnectionIdentity,
) -> None:
    expected = connection_identity_digest(identity)
    if attestation.observed_identity_digest != expected:
        raise ValueError("attestation does not bind execution identity")
    if attestation.continuity is not ContinuityState.CONTINUOUS:
        raise ValueError("session identity continuity is not established")
    if canonical_digest(dict(attestation.observed_identity)) != expected:
        raise ValueError("attested identity snapshot digest mismatch")
