from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable

CapabilityId = str


class SemanticDimension(StrEnum):
    RELATIONAL = "relational"
    DOCUMENT_JSON = "document_json"
    NESTED = "nested"
    GRAPH = "graph"
    VECTOR = "vector"
    GEOSPATIAL = "geospatial"
    TEMPORAL = "temporal"
    STREAMING = "streaming"
    ANALYTICAL = "analytical"
    TRANSACTIONAL = "transactional"
    PROCEDURAL = "procedural"
    ADMINISTRATIVE = "administrative"
    FEDERATED = "federated"


class TranslationFidelity(StrEnum):
    EXACT = "EXACT"
    CONSTRUCTIVE = "CONSTRUCTIVE"
    LOSSY = "LOSSY"
    UNREPRESENTABLE = "UNREPRESENTABLE"

    @property
    def severity(self) -> int:
        return {
            TranslationFidelity.EXACT: 0,
            TranslationFidelity.CONSTRUCTIVE: 1,
            TranslationFidelity.LOSSY: 2,
            TranslationFidelity.UNREPRESENTABLE: 3,
        }[self]


@dataclass(frozen=True, slots=True)
class DialectGenome:
    dialect_id: str
    family: str
    engine: str
    version_selector: str
    capabilities: frozenset[CapabilityId]
    semantic_dimensions: frozenset[SemanticDimension]
    aliases: frozenset[str] = field(default_factory=frozenset)
    notes: tuple[str, ...] = ()

    def supports(self, capability: CapabilityId) -> bool:
        return capability in self.capabilities

    def supports_all(self, capabilities: Iterable[CapabilityId]) -> bool:
        return set(capabilities).issubset(self.capabilities)


@dataclass(frozen=True, slots=True)
class RewriteRule:
    name: str
    source_capability: CapabilityId
    target_capabilities: frozenset[CapabilityId]
    fidelity: TranslationFidelity
    description: str
    target_dialects: frozenset[str] = field(default_factory=frozenset)

    def applies_to(self, target: DialectGenome) -> bool:
        if self.target_dialects and target.dialect_id not in self.target_dialects:
            return False
        return target.supports_all(self.target_capabilities)


@dataclass(frozen=True, slots=True)
class AppliedRewrite:
    source_capability: CapabilityId
    rule_name: str
    fidelity: TranslationFidelity
    description: str


@dataclass(frozen=True, slots=True)
class TranslationPlan:
    source_dialect: str
    target_dialect: str
    required_capabilities: frozenset[CapabilityId]
    native_capabilities: frozenset[CapabilityId]
    missing_capabilities: frozenset[CapabilityId]
    unresolved_capabilities: frozenset[CapabilityId]
    rewrites: tuple[AppliedRewrite, ...]
    fidelity: TranslationFidelity
    fidelity_scope: str = "CAPABILITY_PLAN"
    behavioral_equivalence: str = "NOT_ESTABLISHED"

    def as_dict(self) -> dict[str, object]:
        return {
            "source_dialect": self.source_dialect,
            "target_dialect": self.target_dialect,
            "required_capabilities": sorted(self.required_capabilities),
            "native_capabilities": sorted(self.native_capabilities),
            "missing_capabilities": sorted(self.missing_capabilities),
            "unresolved_capabilities": sorted(self.unresolved_capabilities),
            "rewrites": [
                {
                    "source_capability": rewrite.source_capability,
                    "rule_name": rewrite.rule_name,
                    "fidelity": rewrite.fidelity.value,
                    "description": rewrite.description,
                }
                for rewrite in self.rewrites
            ],
            "fidelity": self.fidelity.value,
            "fidelity_scope": self.fidelity_scope,
            "behavioral_equivalence": self.behavioral_equivalence,
        }
