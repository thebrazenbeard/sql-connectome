from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from sql_connectome.receipts import canonical_digest


class CoercionContext(StrEnum):
    EXPLICIT_CAST = "EXPLICIT_CAST"
    ASSIGNMENT = "ASSIGNMENT"
    COMPARISON = "COMPARISON"
    ARITHMETIC = "ARITHMETIC"
    FUNCTION_ARGUMENT = "FUNCTION_ARGUMENT"
    SET_OPERATION = "SET_OPERATION"
    CASE_RESULT = "CASE_RESULT"
    COALESCE_RESULT = "COALESCE_RESULT"
    LITERAL_RESOLUTION = "LITERAL_RESOLUTION"
    PARAMETER_BINDING = "PARAMETER_BINDING"
    GENERIC_EXPRESSION = "GENERIC_EXPRESSION"


class CoercionPermission(StrEnum):
    ALLOWED = "ALLOWED"
    REJECTED = "REJECTED"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


class CoercionInvocation(StrEnum):
    EXPLICIT_ONLY = "EXPLICIT_ONLY"
    IMPLICIT = "IMPLICIT"
    ENGINE_SELECTED = "ENGINE_SELECTED"
    UNKNOWN = "UNKNOWN"


class EvidenceBasis(StrEnum):
    DEPENDENCY_METADATA = "DEPENDENCY_METADATA"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    ENGINE_CATALOG = "ENGINE_CATALOG"
    ENGINE_PROBE = "ENGINE_PROBE"
    FORMAL_SPECIFICATION = "FORMAL_SPECIFICATION"
    DERIVED_INFERENCE = "DERIVED_INFERENCE"


class QualificationState(StrEnum):
    PROPOSED = "PROPOSED"
    SOURCE_BOUND = "SOURCE_BOUND"
    HOSTILE_REVIEWED = "HOSTILE_REVIEWED"
    BEHAVIORALLY_PROBED = "BEHAVIORALLY_PROBED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    QUALIFIED = "QUALIFIED"


class EffectState(StrEnum):
    UNKNOWN = "UNKNOWN"
    PRESERVED = "PRESERVED"
    CHANGED = "CHANGED"
    LOST = "LOST"
    CONDITIONAL = "CONDITIONAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class TypeIdentity:
    dialect_type: str
    canonical_family: str

    def as_dict(self) -> dict[str, str]:
        return {
            "dialect_type": self.dialect_type,
            "canonical_family": self.canonical_family,
        }


@dataclass(frozen=True, slots=True)
class CoercionScope:
    engine: str
    dialect: str
    context: CoercionContext
    exact_version: str | None = None
    min_version: str | None = None
    max_version: str | None = None
    predicates: tuple[tuple[str, str], ...] = ()
    session: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "dialect": self.dialect,
            "context": self.context.value,
            "exact_version": self.exact_version,
            "min_version": self.min_version,
            "max_version": self.max_version,
            "predicates": dict(sorted(self.predicates)),
            "session": dict(sorted(self.session)),
        }


@dataclass(frozen=True, slots=True)
class CoercionEffects:
    precision_scale: EffectState = EffectState.UNKNOWN
    range: EffectState = EffectState.UNKNOWN
    nullability: EffectState = EffectState.UNKNOWN
    character_set: EffectState = EffectState.UNKNOWN
    collation: EffectState = EffectState.UNKNOWN
    timezone: EffectState = EffectState.UNKNOWN
    representation: EffectState = EffectState.UNKNOWN

    def as_dict(self) -> dict[str, str]:
        return {
            "precision_scale": self.precision_scale.value,
            "range": self.range.value,
            "nullability": self.nullability.value,
            "character_set": self.character_set.value,
            "collation": self.collation.value,
            "timezone": self.timezone.value,
            "representation": self.representation.value,
        }


@dataclass(frozen=True, slots=True)
class CoercionEvidence:
    evidence_id: str
    source: TypeIdentity
    target: TypeIdentity
    scope: CoercionScope
    basis: EvidenceBasis
    qualification: QualificationState
    permission: CoercionPermission = CoercionPermission.UNKNOWN
    invocation: CoercionInvocation = CoercionInvocation.UNKNOWN
    effects: CoercionEffects = field(default_factory=CoercionEffects)
    native_metadata: tuple[tuple[str, str], ...] = ()
    provenance: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "SQL_CONNECTOME_COERCION_EVIDENCE_V1",
            "evidence_id": self.evidence_id,
            "source": self.source.as_dict(),
            "target": self.target.as_dict(),
            "scope": self.scope.as_dict(),
            "basis": self.basis.value,
            "qualification": self.qualification.value,
            "permission": self.permission.value,
            "invocation": self.invocation.value,
            "effects": self.effects.as_dict(),
            "native_metadata": dict(sorted(self.native_metadata)),
            "provenance": dict(sorted(self.provenance)),
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


@dataclass(frozen=True, slots=True)
class CoercionClaim:
    source: TypeIdentity
    target: TypeIdentity
    scope: CoercionScope
    permission: CoercionPermission
    invocation: CoercionInvocation
    effects: CoercionEffects = field(default_factory=CoercionEffects)

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source.as_dict(),
            "target": self.target.as_dict(),
            "scope": self.scope.as_dict(),
            "permission": self.permission.value,
            "invocation": self.invocation.value,
            "effects": self.effects.as_dict(),
        }



class ClaimLookupState(StrEnum):
    QUALIFIED = "QUALIFIED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    evidence: tuple[CoercionEvidence, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class ClaimLookupResult:
    state: ClaimLookupState
    claim: CoercionClaim | None = None
    evidence_ids: tuple[str, ...] = ()


def reconcile_coercion_evidence(
    evidence: tuple[CoercionEvidence, ...] | list[CoercionEvidence],
) -> ReconciliationResult:
    ordered = tuple(sorted(evidence, key=lambda item: (item.evidence_id, item.digest())))
    return ReconciliationResult(
        evidence=ordered,
        digest=canonical_digest([item.as_dict() for item in ordered]),
    )


def _scope_matches(candidate: CoercionScope, query: CoercionScope) -> bool:
    if (
        candidate.engine != query.engine
        or candidate.dialect != query.dialect
        or candidate.context != query.context
    ):
        return False
    if candidate.exact_version is not None and candidate.exact_version != query.exact_version:
        return False
    if not set(candidate.predicates).issubset(set(query.predicates)):
        return False
    return set(candidate.session).issubset(set(query.session))


def _specificity(scope: CoercionScope) -> int:
    return (
        int(scope.exact_version is not None)
        + int(scope.min_version is not None)
        + int(scope.max_version is not None)
        + len(scope.predicates)
        + len(scope.session)
    )


def lookup_coercion_claim(
    reconciled: ReconciliationResult,
    source: TypeIdentity,
    target: TypeIdentity,
    scope: CoercionScope,
) -> ClaimLookupResult:
    qualified = [
        item
        for item in reconciled.evidence
        if item.qualification is QualificationState.QUALIFIED
        and item.source == source
        and item.target == target
        and _scope_matches(item.scope, scope)
    ]
    if not qualified:
        return ClaimLookupResult(state=ClaimLookupState.UNKNOWN)

    specificity = max(_specificity(item.scope) for item in qualified)
    selected = [item for item in qualified if _specificity(item.scope) == specificity]
    signatures = {
        (
            item.permission,
            item.invocation,
            tuple(item.effects.as_dict().items()),
        )
        for item in selected
    }
    evidence_ids = tuple(item.evidence_id for item in selected)
    if len(signatures) != 1:
        return ClaimLookupResult(
            state=ClaimLookupState.CONTRADICTED,
            evidence_ids=evidence_ids,
        )

    exemplar = selected[0]
    return ClaimLookupResult(
        state=ClaimLookupState.QUALIFIED,
        claim=CoercionClaim(
            source=exemplar.source,
            target=exemplar.target,
            scope=exemplar.scope,
            permission=exemplar.permission,
            invocation=exemplar.invocation,
            effects=exemplar.effects,
        ),
        evidence_ids=evidence_ids,
    )



def coercion_semantics_manifest(
    evidence: tuple[CoercionEvidence, ...] | list[CoercionEvidence],
) -> dict[str, object]:
    reconciled = reconcile_coercion_evidence(evidence)
    return {
        "schema": "SQL_CONNECTOME_COERCION_SEMANTICS_V1",
        "reconciler": "SQL_CONNECTOME_COERCION_RECONCILER_V1",
        "evidence_set_digest": reconciled.digest,
        "evidence_count": len(reconciled.evidence),
        "behavioral_equivalence": "NOT_ESTABLISHED",
        "unknown_policy": "PRESERVE",
        "conflict_policy": "CONTRADICTED",
    }
