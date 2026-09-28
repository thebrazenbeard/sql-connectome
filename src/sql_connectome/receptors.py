from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .receipts import canonical_digest


class ReceptorLanguage(StrEnum):
    PRQL = "PRQL"
    CYPHER = "CYPHER"
    SPARQL = "SPARQL"
    DATAFRAME = "DATAFRAME"


class MappingState(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class ExternalPlan:
    language: ReceptorLanguage
    source_version: str | None
    source_digest: str
    constructs: tuple[str, ...]
    source_provenance: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_EXTERNAL_PLAN_V1",
            "language": self.language.value,
            "source_version": self.source_version,
            "source_digest": self.source_digest,
            "constructs": list(self.constructs),
            "source_provenance": list(self.source_provenance),
        }


@dataclass(frozen=True, slots=True)
class ReceptorMapping:
    receptor_version: str
    external_plan_digest: str
    state: MappingState
    supported_constructs: tuple[str, ...]
    unsupported_constructs: tuple[str, ...]
    semantic_losses: tuple[str, ...]
    logical_plan_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_RECEPTOR_MAPPING_V1",
            "receptor_version": self.receptor_version,
            "external_plan_digest": self.external_plan_digest,
            "state": self.state.value,
            "supported_constructs": list(self.supported_constructs),
            "unsupported_constructs": list(self.unsupported_constructs),
            "semantic_losses": list(self.semantic_losses),
            "logical_plan_digest": self.logical_plan_digest,
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


def external_plan_digest(plan: ExternalPlan) -> str:
    return canonical_digest(plan.as_dict())
