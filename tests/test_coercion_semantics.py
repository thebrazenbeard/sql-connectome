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
    result = lookup_coercion_claim(left, exact_allow.source, exact_allow.target, query)
    assert result.state is ClaimLookupState.CONTRADICTED
    assert set(result.evidence_ids) == {"exact-a", "exact-b"}

    unknown = lookup_coercion_claim(
        left,
        exact_allow.source,
        exact_allow.target,
        CoercionScope(
            engine="postgresql",
            dialect="postgres",
            exact_version="18",
            context=CoercionContext.COMPARISON,
        ),
    )
    assert unknown.state is ClaimLookupState.UNKNOWN


def test_dependency_projection_is_non_behavioral_and_v1_graph_is_unchanged() -> None:
    from sql_connectome.connectome.type_system import (
        dependency_coercion_evidence,
        dialect_type_graph,
    )

    graph = dialect_type_graph(dialect_id="postgres", parser_dialect="postgres")
    evidence = dependency_coercion_evidence(
        dialect_id="postgres",
        parser_dialect="postgres",
    )

    assert graph["schema"] == "SQL_CONNECTOME_TYPE_GRAPH_V1"
    assert graph["missing_edge_meaning"] == "UNKNOWN_NOT_UNSUPPORTED"
    assert len(evidence) == len(graph["implicit_coercions"])
    assert all(item.basis is EvidenceBasis.DEPENDENCY_METADATA for item in evidence)
    assert all(item.qualification is QualificationState.SOURCE_BOUND for item in evidence)
    assert all(
        dict(item.provenance)["evidence_ceiling"] == "DEPENDENCY_METADATA" for item in evidence
    )


def test_manifest_is_deterministic_and_evidence_bound() -> None:
    from sql_connectome.connectome.coercion_semantics import coercion_semantics_manifest

    first = coercion_semantics_manifest(())
    second = coercion_semantics_manifest(())
    assert first == second
    assert first["schema"] == "SQL_CONNECTOME_COERCION_SEMANTICS_V1"
    assert first["reconciler"] == "SQL_CONNECTOME_COERCION_RECONCILER_V1"
    assert first["behavioral_equivalence"] == "NOT_ESTABLISHED"

    evidence = _evidence("manifest-evidence", version="17", permission=CoercionPermission.ALLOWED)
    changed = coercion_semantics_manifest((evidence,))
    assert changed["evidence_set_digest"] != first["evidence_set_digest"]


def test_lookup_is_bound_to_source_and_target_identity() -> None:
    from sql_connectome.connectome.coercion_semantics import (
        ClaimLookupState,
        lookup_coercion_claim,
        reconcile_coercion_evidence,
    )

    wanted = _evidence("wanted", version="17", permission=CoercionPermission.ALLOWED)
    unrelated = CoercionEvidence(
        evidence_id="unrelated",
        source=TypeIdentity("TEXT", "STRING"),
        target=TypeIdentity("INT", "INTEGER"),
        scope=wanted.scope,
        basis=EvidenceBasis.ENGINE_CATALOG,
        qualification=QualificationState.QUALIFIED,
        permission=CoercionPermission.REJECTED,
        invocation=CoercionInvocation.ENGINE_SELECTED,
    )
    result = lookup_coercion_claim(
        reconcile_coercion_evidence((wanted, unrelated)),
        wanted.source,
        wanted.target,
        wanted.scope,
    )
    assert result.state is ClaimLookupState.QUALIFIED
    assert result.evidence_ids == ("wanted",)


def test_lookup_is_bound_to_source_and_target_identity() -> None:
    from sql_connectome.connectome.coercion_semantics import (
        ClaimLookupState,
        lookup_coercion_claim,
        reconcile_coercion_evidence,
    )

    wanted = _evidence("wanted", version="17", permission=CoercionPermission.ALLOWED)
    unrelated = CoercionEvidence(
        evidence_id="unrelated",
        source=TypeIdentity("TEXT", "STRING"),
        target=TypeIdentity("INT", "INTEGER"),
        scope=wanted.scope,
        basis=EvidenceBasis.ENGINE_CATALOG,
        qualification=QualificationState.QUALIFIED,
        permission=CoercionPermission.REJECTED,
        invocation=CoercionInvocation.ENGINE_SELECTED,
    )
    result = lookup_coercion_claim(
        reconcile_coercion_evidence((wanted, unrelated)),
        wanted.source,
        wanted.target,
        wanted.scope,
    )
    assert result.state is ClaimLookupState.QUALIFIED
    assert result.evidence_ids == ("wanted",)


def test_lookup_is_bound_to_source_and_target_identity() -> None:
    from sql_connectome.connectome.coercion_semantics import (
        ClaimLookupState,
        lookup_coercion_claim,
        reconcile_coercion_evidence,
    )

    wanted = _evidence("wanted", version="17", permission=CoercionPermission.ALLOWED)
    unrelated = CoercionEvidence(
        evidence_id="unrelated",
        source=TypeIdentity("TEXT", "STRING"),
        target=TypeIdentity("INT", "INTEGER"),
        scope=wanted.scope,
        basis=EvidenceBasis.ENGINE_CATALOG,
        qualification=QualificationState.QUALIFIED,
        permission=CoercionPermission.REJECTED,
        invocation=CoercionInvocation.ENGINE_SELECTED,
    )
    result = lookup_coercion_claim(
        reconcile_coercion_evidence((wanted, unrelated)),
        wanted.source,
        wanted.target,
        wanted.scope,
    )
    assert result.state is ClaimLookupState.QUALIFIED
    assert result.evidence_ids == ("wanted",)
