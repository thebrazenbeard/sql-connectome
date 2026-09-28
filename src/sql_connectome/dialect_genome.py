from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .receipts import canonical_digest


class EvidenceClass(StrEnum):
    DEPENDENCY_METADATA = "DEPENDENCY_METADATA"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    ENGINE_PROBE = "ENGINE_PROBE"


class EvidenceCurrentness(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    VERSION_MISMATCH = "VERSION_MISMATCH"


class ReconciliationState(StrEnum):
    AGREES = "AGREES"
    CONFLICTS = "CONFLICTS"
    INSUFFICIENT = "INSUFFICIENT"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class DialectObservation:
    dialect: str
    claim_key: str
    evidence_class: EvidenceClass
    observed_value: str
    source_locator: str
    source_digest: str
    source_version: str | None = None
    engine_version: str | None = None
    acquired_at: str | None = None
    currentness: EvidenceCurrentness = EvidenceCurrentness.UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_DIALECT_OBSERVATION_V1",
            "dialect": self.dialect,
            "claim_key": self.claim_key,
            "evidence_class": self.evidence_class.value,
            "observed_value": self.observed_value,
            "source_locator": self.source_locator,
            "source_digest": self.source_digest,
            "source_version": self.source_version,
            "engine_version": self.engine_version,
            "acquired_at": self.acquired_at,
            "currentness": self.currentness.value,
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


@dataclass(frozen=True, slots=True)
class DialectClaimReconciliation:
    dialect: str
    claim_key: str
    state: ReconciliationState
    observation_digests: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_DIALECT_RECONCILIATION_V1",
            "dialect": self.dialect,
            "claim_key": self.claim_key,
            "state": self.state.value,
            "observation_digests": list(self.observation_digests),
            "reason": self.reason,
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


def reconcile_claim(
    observations: tuple[DialectObservation, ...],
) -> DialectClaimReconciliation:
    if not observations:
        raise ValueError("at least one observation is required")
    dialect = observations[0].dialect
    claim_key = observations[0].claim_key
    if any(item.dialect != dialect or item.claim_key != claim_key for item in observations):
        raise ValueError("reconciliation observations must share dialect and claim key")
    digests = tuple(item.digest() for item in observations)
    usable = tuple(
        item
        for item in observations
        if item.currentness not in {EvidenceCurrentness.STALE, EvidenceCurrentness.VERSION_MISMATCH}
    )
    if not usable:
        return DialectClaimReconciliation(
            dialect, claim_key, ReconciliationState.STALE, digests, "no current/unknown evidence"
        )
    values = {item.observed_value for item in usable}
    classes = {item.evidence_class for item in usable}
    if len(values) > 1:
        state = ReconciliationState.CONFLICTS
        reason = "independent observations disagree"
    elif len(classes) < 2:
        state = ReconciliationState.INSUFFICIENT
        reason = "single evidence class cannot corroborate claim"
    else:
        state = ReconciliationState.AGREES
        reason = "multiple evidence classes report the same value"
    return DialectClaimReconciliation(dialect, claim_key, state, digests, reason)


@dataclass(frozen=True, slots=True)
class DialectGenome:
    dialect: str
    target_version: str | None
    acquisition_policy_version: str
    observations: tuple[DialectObservation, ...]
    reconciliations: tuple[DialectClaimReconciliation, ...]

    def __post_init__(self) -> None:
        if any(item.dialect != self.dialect for item in self.observations):
            raise ValueError("genome cannot contain another dialect")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_DIALECT_GENOME_V1",
            "dialect": self.dialect,
            "target_version": self.target_version,
            "acquisition_policy_version": self.acquisition_policy_version,
            "observation_digests": [item.digest() for item in self.observations],
            "reconciliation_digests": [item.digest() for item in self.reconciliations],
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())
