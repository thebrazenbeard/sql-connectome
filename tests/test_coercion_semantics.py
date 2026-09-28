from sql_connectome.connectome.coercion_semantics import (
    CoercionContext,
    CoercionEffects,
    CoercionEvidence,
    CoercionInvocation,
    CoercionPermission,
    CoercionScope,
    EffectState,
    EvidenceBasis,
    QualificationState,
    TypeIdentity,
)


def test_evidence_schema_preserves_direction_native_metadata_and_unknown_effects() -> None:
    scope = CoercionScope(
        engine="postgresql",
        dialect="postgres",
        exact_version="17",
        context=CoercionContext.ASSIGNMENT,
        session=(("timezone", "UTC"),),
    )
    evidence = CoercionEvidence(
        evidence_id="pg:int4->int8:assignment",
        source=TypeIdentity("INT", "INTEGER"),
        target=TypeIdentity("BIGINT", "INTEGER"),
        scope=scope,
        basis=EvidenceBasis.ENGINE_CATALOG,
        qualification=QualificationState.SOURCE_BOUND,
        permission=CoercionPermission.ALLOWED,
        invocation=CoercionInvocation.ENGINE_SELECTED,
        native_metadata=(("castcontext", "a"), ("castmethod", "f")),
    )

    payload = evidence.as_dict()

    assert payload["source"]["dialect_type"] == "INT"
    assert payload["target"]["dialect_type"] == "BIGINT"
    assert payload["native_metadata"] == {"castcontext": "a", "castmethod": "f"}
    assert payload["effects"] == CoercionEffects().as_dict()
    assert set(payload["effects"].values()) == {EffectState.UNKNOWN.value}
    assert evidence.digest() == evidence.digest()



def _evidence(
    evidence_id: str, *, version: str | None, permission: CoercionPermission
) -> CoercionEvidence:
    return CoercionEvidence(
        evidence_id=evidence_id,
        source=TypeIdentity("INT", "INTEGER"),
        target=TypeIdentity("BIGINT", "INTEGER"),
        scope=CoercionScope(
            engine="postgresql",
            dialect="postgres",
            exact_version=version,
            context=CoercionContext.ASSIGNMENT,
        ),
        basis=EvidenceBasis.ENGINE_CATALOG,
        qualification=QualificationState.QUALIFIED,
        permission=permission,
        invocation=CoercionInvocation.ENGINE_SELECTED,
    )


def test_reconciliation_is_order_independent_and_lookup_preserves_conflict() -> None:
    from sql_connectome.connectome.coercion_semantics import (
        ClaimLookupState,
        lookup_coercion_claim,
        reconcile_coercion_evidence,
    )

    broad = _evidence("broad", version=None, permission=CoercionPermission.ALLOWED)
    exact_allow = _evidence("exact-a", version="17", permission=CoercionPermission.ALLOWED)
    exact_reject = _evidence("exact-b", version="17", permission=CoercionPermission.REJECTED)

    left = reconcile_coercion_evidence((broad, exact_allow, exact_reject))
    right = reconcile_coercion_evidence((exact_reject, broad, exact_allow))
    assert left.digest == right.digest

    query = CoercionScope(
        engine="postgresql",
        dialect="postgres",
        exact_version="17",
        context=CoercionContext.ASSIGNMENT,
    )
    result = lookup_coercion_claim(left, query)
    assert result.state is ClaimLookupState.CONTRADICTED
    assert set(result.evidence_ids) == {"exact-a", "exact-b"}

    unknown = lookup_coercion_claim(
        left,
        CoercionScope(
            engine="postgresql",
            dialect="postgres",
            exact_version="18",
            context=CoercionContext.COMPARISON,
        ),
    )
    assert unknown.state is ClaimLookupState.UNKNOWN
