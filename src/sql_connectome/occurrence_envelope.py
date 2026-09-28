from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .receipts import canonical_digest


@dataclass(frozen=True, slots=True)
class OccurrenceEnvelope:
    receipt_digest: str
    occurrence_id: str
    issued_at: str
    nonce: str
    signer_id: str | None = None
    signature_algorithm: str | None = None
    signature: str | None = None

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": "SQL_CONNECTOME_OCCURRENCE_ENVELOPE_V1",
            "receipt_digest": self.receipt_digest,
            "occurrence_id": self.occurrence_id,
            "issued_at": self.issued_at,
            "nonce": self.nonce,
            "signer_id": self.signer_id,
            "signature_algorithm": self.signature_algorithm,
        }

    def as_dict(self) -> dict[str, object]:
        return {**self.unsigned_payload(), "signature": self.signature}

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


class SignatureVerifier(Protocol):
    def verify(
        self,
        *,
        signer_id: str,
        algorithm: str,
        payload_digest: str,
        signature: str,
    ) -> bool: ...


class ReplayGuard(Protocol):
    def accept_once(self, occurrence_digest: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class TrustPolicy:
    require_signature: bool = False
    allowed_signers: tuple[str, ...] = ()


class InMemoryReplayGuard:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def accept_once(self, occurrence_digest: str) -> bool:
        if occurrence_digest in self._seen:
            return False
        self._seen.add(occurrence_digest)
        return True


def occurrence_payload_digest(envelope: OccurrenceEnvelope) -> str:
    return canonical_digest(envelope.unsigned_payload())


def verify_occurrence(
    envelope: OccurrenceEnvelope,
    *,
    policy: TrustPolicy,
    verifier: SignatureVerifier | None = None,
    replay_guard: ReplayGuard | None = None,
) -> None:
    signed = all(
        (envelope.signer_id, envelope.signature_algorithm, envelope.signature)
    )
    if policy.require_signature and not signed:
        raise ValueError("trusted occurrence requires a signature")
    if policy.allowed_signers:
        if envelope.signer_id not in policy.allowed_signers:
            raise ValueError("occurrence signer is not trusted")
    if signed:
        if verifier is None:
            raise ValueError("signed occurrence requires a verifier")
        if not verifier.verify(
            signer_id=envelope.signer_id or "",
            algorithm=envelope.signature_algorithm or "",
            payload_digest=occurrence_payload_digest(envelope),
            signature=envelope.signature or "",
        ):
            raise ValueError("occurrence signature verification failed")
    if replay_guard is not None and not replay_guard.accept_once(envelope.digest()):
        raise ValueError("occurrence replay detected")
