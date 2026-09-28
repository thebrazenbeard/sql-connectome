from sql_connectome.connectome.coercion_semantics import (
    CoercionContext,
    CoercionInvocation,
    CoercionPermission,
    EffectState,
    EvidenceBasis,
)
from sql_connectome.connectome.coercion_sources import postgresql_pg_cast_evidence


def test_postgresql_pg_cast_preserves_native_categories_without_universalizing_them() -> None:
    rows = [
        {
            "source_type": "int4",
            "target_type": "int8",
            "source_family": "INTEGER",
            "target_family": "INTEGER",
            "castcontext": "a",
            "castmethod": "f",
        }
    ]
    evidence = postgresql_pg_cast_evidence(
        rows,
        engine_version="17.0",
        provenance=(("catalog", "pg_cast"),),
    )
    item = evidence[0]
    assert item.basis is EvidenceBasis.ENGINE_CATALOG
    assert item.scope.context is CoercionContext.ASSIGNMENT
    assert item.invocation is CoercionInvocation.ENGINE_SELECTED
    assert item.permission is CoercionPermission.ALLOWED
    assert dict(item.native_metadata) == {"castcontext": "a", "castmethod": "f"}
    assert item.effects.representation is EffectState.UNKNOWN


def test_pg_cast_explicit_context_maps_only_to_explicit_invocation() -> None:
    evidence = postgresql_pg_cast_evidence(
        [
            {
                "source_type": "text",
                "target_type": "int4",
                "source_family": "STRING",
                "target_family": "INTEGER",
                "castcontext": "e",
                "castmethod": "i",
            }
        ],
        engine_version="17.0",
        provenance=(),
    )
    assert evidence[0].scope.context is CoercionContext.EXPLICIT_CAST
    assert evidence[0].invocation is CoercionInvocation.EXPLICIT_ONLY
