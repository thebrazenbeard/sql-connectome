from __future__ import annotations

from collections.abc import Iterable, Mapping

from .coercion_semantics import (
    CoercionContext,
    CoercionEvidence,
    CoercionInvocation,
    CoercionPermission,
    CoercionScope,
    EvidenceBasis,
    QualificationState,
    TypeIdentity,
)


_CONTEXT = {
    "i": (CoercionContext.GENERIC_EXPRESSION, CoercionInvocation.IMPLICIT),
    "a": (CoercionContext.ASSIGNMENT, CoercionInvocation.ENGINE_SELECTED),
    "e": (CoercionContext.EXPLICIT_CAST, CoercionInvocation.EXPLICIT_ONLY),
}


def postgresql_pg_cast_evidence(
    rows: Iterable[Mapping[str, object]],
    *,
    engine_version: str,
    provenance: tuple[tuple[str, str], ...],
) -> tuple[CoercionEvidence, ...]:
    evidence: list[CoercionEvidence] = []
    for index, row in enumerate(rows):
        native_context = str(row["castcontext"])
        context, invocation = _CONTEXT.get(
            native_context,
            (CoercionContext.GENERIC_EXPRESSION, CoercionInvocation.UNKNOWN),
        )
        source_type = str(row["source_type"])
        target_type = str(row["target_type"])
        evidence.append(
            CoercionEvidence(
                evidence_id=(
                    f"postgresql:{engine_version}:pg_cast:"
                    f"{source_type}->{target_type}:{native_context}:{index}"
                ),
                source=TypeIdentity(source_type, str(row["source_family"])),
                target=TypeIdentity(target_type, str(row["target_family"])),
                scope=CoercionScope(
                    engine="postgresql",
                    dialect="postgres",
                    exact_version=engine_version,
                    context=context,
                ),
                basis=EvidenceBasis.ENGINE_CATALOG,
                qualification=QualificationState.SOURCE_BOUND,
                permission=CoercionPermission.ALLOWED,
                invocation=invocation,
                native_metadata=(
                    ("castcontext", native_context),
                    ("castmethod", str(row["castmethod"])),
                ),
                provenance=provenance,
            )
        )
    return tuple(evidence)
