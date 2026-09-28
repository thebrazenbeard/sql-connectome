from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sql_connectome.receipts import canonical_digest

from .model import AppliedRewrite, RewriteRule, TranslationPlan
from .registry import DEFAULT_REWRITE_RULES


class RewriteQualification(StrEnum):
    QUALIFIED = "QUALIFIED"
    CONDITIONAL = "CONDITIONAL"
    UNQUALIFIED = "UNQUALIFIED"


@dataclass(frozen=True, slots=True)
class GovernedRewrite:
    rewrite_id: str
    rule_name: str
    source_capability: str
    rule_version: str
    qualification: RewriteQualification
    required_evidence: tuple[str, ...]
    observed_evidence: tuple[str, ...]
    preconditions: tuple[str, ...]
    unresolved_semantics: tuple[str, ...]
    behavioral_equivalence: str = "NOT_ESTABLISHED"

    def as_dict(self) -> dict[str, object]:
        return {
            "rewrite_id": self.rewrite_id,
            "rule_name": self.rule_name,
            "source_capability": self.source_capability,
            "rule_version": self.rule_version,
            "qualification": self.qualification.value,
            "required_evidence": list(self.required_evidence),
            "observed_evidence": list(self.observed_evidence),
            "preconditions": list(self.preconditions),
            "unresolved_semantics": list(self.unresolved_semantics),
            "behavioral_equivalence": self.behavioral_equivalence,
        }


def _rule_digest(rule: RewriteRule) -> str:
    return canonical_digest(
        {
            "name": rule.name,
            "source_capability": rule.source_capability,
            "target_capabilities": sorted(rule.target_capabilities),
            "target_dialects": sorted(rule.target_dialects),
            "fidelity": rule.fidelity.value,
            "description": rule.description,
        }
    )


_RULE_GOVERNANCE: dict[str, dict[str, tuple[str, ...] | str]] = {
    "qualify-via-derived-table": {
        "version": "1",
        "evidence": ("CAPABILITY_REGISTRY", "TARGET_PARSE"),
        "preconditions": (
            "window_functions admitted by target",
            "derived_tables admitted by target",
        ),
        "unresolved": ("window-frame and alias-resolution behavioral equivalence",),
    },
    "apply-via-lateral": {
        "version": "1",
        "evidence": ("CAPABILITY_REGISTRY",),
        "preconditions": ("lateral_join admitted by target",),
        "unresolved": ("correlation and side-effect equivalence",),
    },
    "connect-by-via-recursive-cte": {
        "version": "1",
        "evidence": ("CAPABILITY_REGISTRY",),
        "preconditions": ("recursive_cte admitted by target",),
        "unresolved": (
            "Oracle hierarchy pseudocolumn semantics",
            "cycle semantics",
            "sibling ordering",
        ),
    },
    "variant-via-json": {
        "version": "1",
        "evidence": ("CAPABILITY_REGISTRY", "TYPE_SEMANTICS"),
        "preconditions": ("json admitted by target",),
        "unresolved": ("typed value, comparison, and coercion equivalence",),
    },
    "struct-via-json": {
        "version": "1",
        "evidence": ("CAPABILITY_REGISTRY", "TYPE_SEMANTICS"),
        "preconditions": ("json admitted by target",),
        "unresolved": ("structured-record type and comparison equivalence",),
    },
}


def _govern(
    rewrite: AppliedRewrite,
    observed_evidence: frozenset[str],
) -> GovernedRewrite:
    record = _RULE_GOVERNANCE.get(rewrite.rule_name)
    if record is None:
        return GovernedRewrite(
            rewrite_id=f"{rewrite.rule_name}@UNVERSIONED",
            rule_name=rewrite.rule_name,
            source_capability=rewrite.source_capability,
            rule_version="UNVERSIONED",
            qualification=RewriteQualification.UNQUALIFIED,
            required_evidence=(),
            observed_evidence=(),
            preconditions=(),
            unresolved_semantics=("no governed rewrite record",),
        )

    canonical_rule = next(
        (item for item in DEFAULT_REWRITE_RULES if item.name == rewrite.rule_name),
        None,
    )
    expected_digest = _rule_digest(canonical_rule) if canonical_rule is not None else None
    if rewrite.rule_definition_digest != expected_digest:
        return GovernedRewrite(
            rewrite_id=f"{rewrite.rule_name}@DEFINITION_MISMATCH",
            rule_name=rewrite.rule_name,
            source_capability=rewrite.source_capability,
            rule_version="DEFINITION_MISMATCH",
            qualification=RewriteQualification.UNQUALIFIED,
            required_evidence=(),
            observed_evidence=(),
            preconditions=(),
            unresolved_semantics=("rewrite definition does not match governed version",),
        )

    unresolved = tuple(record["unresolved"])
    required = tuple(record["evidence"])
    observed = tuple(item for item in required if item in observed_evidence)
    missing = tuple(item for item in required if item not in observed_evidence)
    if missing:
        qualification = RewriteQualification.UNQUALIFIED
        unresolved = unresolved + tuple(f"missing evidence: {item}" for item in missing)
    elif unresolved:
        qualification = RewriteQualification.CONDITIONAL
    else:
        qualification = RewriteQualification.QUALIFIED
    version = str(record["version"])
    return GovernedRewrite(
        rewrite_id=f"{rewrite.rule_name}@{version}",
        rule_name=rewrite.rule_name,
        source_capability=rewrite.source_capability,
        rule_version=version,
        qualification=qualification,
        required_evidence=required,
        observed_evidence=observed,
        preconditions=tuple(record["preconditions"]),
        unresolved_semantics=unresolved,
    )


def govern_translation_plan(
    plan: TranslationPlan,
    *,
    observed_evidence: frozenset[str] = frozenset(),
) -> dict[str, object]:
    rewrites = tuple(_govern(item, observed_evidence) for item in plan.rewrites)
    qualification = (
        RewriteQualification.UNQUALIFIED
        if any(item.qualification is RewriteQualification.UNQUALIFIED for item in rewrites)
        else RewriteQualification.CONDITIONAL
        if any(item.qualification is RewriteQualification.CONDITIONAL for item in rewrites)
        else RewriteQualification.QUALIFIED
    )
    payload = {
        "schema": "SQL_CONNECTOME_GOVERNED_REWRITE_PLAN_V1",
        "source_dialect": plan.source_dialect,
        "target_dialect": plan.target_dialect,
        "qualification": qualification.value,
        "rewrites": [item.as_dict() for item in rewrites],
        "behavioral_equivalence": "NOT_ESTABLISHED",
        "execution_authority": "NONE",
    }
    return {**payload, "digest": canonical_digest(payload)}
