from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CompatibilityState(StrEnum):
    EXACT = "EXACT"
    EXTENSION_REQUIRED = "EXTENSION_REQUIRED"
    UNREPRESENTABLE = "UNREPRESENTABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CompatibilityFinding:
    feature: str
    state: CompatibilityState
    reason: str


@dataclass(frozen=True, slots=True)
class SubstraitCompatibility:
    overall: CompatibilityState
    findings: tuple[CompatibilityFinding, ...]
    authority: str = "INTEROPERABILITY_INSPECTION_ONLY"


_CORE_RELATIONS = {
    "READ",
    "PROJECT",
    "FILTER",
    "JOIN",
    "AGGREGATE",
    "WINDOW",
    "SET_OP",
    "SORT",
    "LIMIT",
    "DISTINCT",
}


def inspect_substrait_compatibility(plan: dict[str, Any]) -> SubstraitCompatibility:
    findings: list[CompatibilityFinding] = []
    for loss in plan.get("losses", ()):
        findings.append(
            CompatibilityFinding(
                f"loss:{loss}",
                CompatibilityState.UNKNOWN,
                "logical-plan derivation records unresolved semantic loss",
            )
        )
    for relation in plan["relations"]:
        kind = relation["kind"]
        if kind in {"JOIN", "SET_OP"}:
            findings.append(
                CompatibilityFinding(
                    f"relation:{kind}",
                    CompatibilityState.EXTENSION_REQUIRED,
                    "V1 plan lacks operator detail for exact Substrait equivalence",
                )
            )
        elif kind in {"SUBQUERY", "LATERAL"}:
            findings.append(
                CompatibilityFinding(
                    f"relation:{kind}",
                    CompatibilityState.EXTENSION_REQUIRED,
                    "scoped SQL relation requires explicit mapping review",
                )
            )
        elif kind not in _CORE_RELATIONS:
            findings.append(
                CompatibilityFinding(
                    f"relation:{kind}",
                    CompatibilityState.UNREPRESENTABLE,
                    "no V1 Substrait receptor mapping",
                )
            )
        for field in relation["output_schema"]:
            if field["logical_type"]["canonical_family"] == "UNKNOWN":
                findings.append(
                    CompatibilityFinding(
                        f"field:{field['field_id']}",
                        CompatibilityState.UNKNOWN,
                        "logical type is not established",
                    )
                )
    if not findings:
        overall = CompatibilityState.EXACT
    elif any(item.state is CompatibilityState.UNREPRESENTABLE for item in findings):
        overall = CompatibilityState.UNREPRESENTABLE
    elif any(item.state is CompatibilityState.UNKNOWN for item in findings):
        overall = CompatibilityState.UNKNOWN
    else:
        overall = CompatibilityState.EXTENSION_REQUIRED
    return SubstraitCompatibility(overall, tuple(findings))
