from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from .model import AppliedRewrite, DialectGenome, RewriteRule, TranslationFidelity, TranslationPlan
from .registry import DEFAULT_DIALECTS, DEFAULT_REWRITE_RULES, resolve_dialect


def _worst_fidelity(values: Iterable[TranslationFidelity]) -> TranslationFidelity:
    values = tuple(values)
    if not values:
        return TranslationFidelity.EXACT
    return max(values, key=lambda value: value.severity)


def plan_translation(
    source_dialect: str,
    target_dialect: str,
    required_capabilities: Iterable[str],
    *,
    dialects: Mapping[str, DialectGenome] | None = None,
    rewrite_rules: Sequence[RewriteRule] = DEFAULT_REWRITE_RULES,
) -> TranslationPlan:
    registry = dialects or DEFAULT_DIALECTS

    if registry is DEFAULT_DIALECTS:
        source = resolve_dialect(source_dialect)
        target = resolve_dialect(target_dialect)
    else:
        try:
            source = registry[source_dialect]
            target = registry[target_dialect]
        except KeyError as exc:
            raise KeyError(f"UNKNOWN_DIALECT:{exc.args[0]}") from exc

    required = frozenset(required_capabilities)
    native = frozenset(capability for capability in required if target.supports(capability))
    missing = frozenset(required - native)

    rewrites: list[AppliedRewrite] = []
    unresolved: set[str] = set()

    for capability in sorted(missing):
        candidates = [
            rule
            for rule in rewrite_rules
            if rule.source_capability == capability and rule.applies_to(target)
        ]
        if not candidates:
            unresolved.add(capability)
            continue

        selected = min(candidates, key=lambda rule: (rule.fidelity.severity, rule.name))
        rewrites.append(
            AppliedRewrite(
                source_capability=capability,
                rule_name=selected.name,
                fidelity=selected.fidelity,
                description=selected.description,
            )
        )

    if unresolved:
        fidelity = TranslationFidelity.UNREPRESENTABLE
    else:
        fidelity = _worst_fidelity(rewrite.fidelity for rewrite in rewrites)

    return TranslationPlan(
        source_dialect=source.dialect_id,
        target_dialect=target.dialect_id,
        required_capabilities=required,
        native_capabilities=native,
        missing_capabilities=missing,
        unresolved_capabilities=frozenset(unresolved),
        rewrites=tuple(rewrites),
        fidelity=fidelity,
    )


def list_dialects() -> list[dict[str, object]]:
    return [
        {
            "dialect_id": genome.dialect_id,
            "family": genome.family,
            "engine": genome.engine,
            "version_selector": genome.version_selector,
            "aliases": sorted(genome.aliases),
            "capabilities": sorted(genome.capabilities),
            "semantic_dimensions": sorted(dimension.value for dimension in genome.semantic_dimensions),
            "notes": list(genome.notes),
        }
        for genome in sorted(DEFAULT_DIALECTS.values(), key=lambda item: item.dialect_id)
    ]
