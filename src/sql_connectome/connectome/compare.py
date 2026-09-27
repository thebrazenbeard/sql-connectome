from __future__ import annotations

from .catalog import DEFAULT_CATALOG, ConnectomeCatalog
from .expression_bindings import probe_expression_dialect_bindings
from .semantics import dialect_semantic_profile
from .type_system import dialect_type_graph


def _set_comparison(source: frozenset[str], target: frozenset[str]) -> dict[str, list[str]]:
    return {
        "shared": sorted(source & target),
        "source_only": sorted(source - target),
        "target_only": sorted(target - source),
    }


def _semantic_flag_differences(
    source_profile: dict[str, object],
    target_profile: dict[str, object],
) -> list[dict[str, object]]:
    source_flags = source_profile["flags"]
    target_flags = target_profile["flags"]
    assert isinstance(source_flags, dict)
    assert isinstance(target_flags, dict)

    differences: list[dict[str, object]] = []
    for flag in sorted(set(source_flags) | set(target_flags)):
        source_value = source_flags.get(flag)
        target_value = target_flags.get(flag)
        if source_value != target_value:
            differences.append(
                {
                    "flag": flag,
                    "source_value": source_value,
                    "target_value": target_value,
                }
            )
    return differences


def _type_graph_summary(graph: dict[str, object]) -> dict[str, object]:
    dialect_types = graph["dialect_types"]
    implicit_coercions = graph["implicit_coercions"]
    assert isinstance(dialect_types, list)
    assert isinstance(implicit_coercions, list)

    return {
        "dialect_id": graph["dialect_id"],
        "parser_dialect": graph["parser_dialect"],
        "dialect_type_count": len(dialect_types),
        "implicit_coercion_count": len(implicit_coercions),
        "evidence_basis": graph["evidence_basis"],
        "evidence_ceiling": graph["evidence_ceiling"],
        "missing_edge_meaning": graph["missing_edge_meaning"],
    }


def _expression_binding_summary(
    payload: dict[str, object],
) -> dict[str, object]:
    bound = payload["roundtrip_bound_semantic_ids"]
    state_counts = payload["state_counts"]
    assert isinstance(bound, list)
    assert isinstance(state_counts, dict)

    return {
        "dialect_id": payload["dialect_id"],
        "parser_dialect": payload["parser_dialect"],
        "probe_count": payload["probe_count"],
        "state_counts": state_counts,
        "roundtrip_bound_count": len(bound),
        "roundtrip_bound_semantic_ids": bound,
        "probe_set_digest": payload["probe_set_digest"],
        "semantic_registry_digest": payload["semantic_registry_digest"],
        "evidence_basis": payload["evidence_basis"],
        "evidence_scope": payload["evidence_scope"],
        "evidence_ceiling": payload["evidence_ceiling"],
    }


def compare_dialects(
    source_dialect: str,
    target_dialect: str,
    *,
    catalog: ConnectomeCatalog = DEFAULT_CATALOG,
) -> dict[str, object]:
    source = catalog.resolve(source_dialect)
    target = catalog.resolve(target_dialect)
    source_parser = catalog.parser_adapter(source.dialect_id)
    target_parser = catalog.parser_adapter(target.dialect_id)

    source_profile = dialect_semantic_profile(source.dialect_id, source_parser)
    target_profile = dialect_semantic_profile(target.dialect_id, target_parser)
    source_graph = dialect_type_graph(
        dialect_id=source.dialect_id,
        parser_dialect=source_parser,
    )
    target_graph = dialect_type_graph(
        dialect_id=target.dialect_id,
        parser_dialect=target_parser,
    )
    source_bindings = probe_expression_dialect_bindings(
        dialect_id=source.dialect_id,
        parser_dialect=source_parser,
        catalog_digest=catalog.digest,
    )
    target_bindings = probe_expression_dialect_bindings(
        dialect_id=target.dialect_id,
        parser_dialect=target_parser,
        catalog_digest=catalog.digest,
    )
    source_bound = frozenset(source_bindings["roundtrip_bound_semantic_ids"])
    target_bound = frozenset(target_bindings["roundtrip_bound_semantic_ids"])

    return {
        "schema": "SQL_CONNECTOME_DIALECT_COMPARISON_V1",
        "catalog_digest": catalog.digest,
        "source": {
            "dialect_id": source.dialect_id,
            "engine": source.engine,
            "family": source.family,
            "version_selector": source.version_selector,
            "parser_dialect": source_parser,
        },
        "target": {
            "dialect_id": target.dialect_id,
            "engine": target.engine,
            "family": target.family,
            "version_selector": target.version_selector,
            "parser_dialect": target_parser,
        },
        "capabilities": _set_comparison(source.capabilities, target.capabilities),
        "semantic_dimensions": _set_comparison(
            frozenset(dimension.value for dimension in source.semantic_dimensions),
            frozenset(dimension.value for dimension in target.semantic_dimensions),
        ),
        "semantic_flags": {
            "source": source_profile,
            "target": target_profile,
            "differences": _semantic_flag_differences(source_profile, target_profile),
            "evidence_basis": "SQLGLOT_DIALECT_FLAGS",
            "evidence_ceiling": "DEPENDENCY_METADATA",
        },
        "type_graphs": {
            "source": _type_graph_summary(source_graph),
            "target": _type_graph_summary(target_graph),
        },
        "expression_bindings": {
            "source": _expression_binding_summary(source_bindings),
            "target": _expression_binding_summary(target_bindings),
            "roundtrip_bound": _set_comparison(source_bound, target_bound),
        },
        "compatibility_score": None,
        "behavioral_equivalence": "NOT_ESTABLISHED",
        "generalization": "NOT_ESTABLISHED",
        "evidence_scope": "CATALOG_AND_PINNED_DEPENDENCY_EVIDENCE",
    }
