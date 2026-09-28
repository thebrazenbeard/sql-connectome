from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sql_connectome.receipts import canonical_digest


class ApplicabilityState(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNRESOLVED = "UNRESOLVED"


class QualificationState(StrEnum):
    STRUCTURAL_ONLY = "STRUCTURAL_ONLY"
    BEHAVIORALLY_QUALIFIED = "BEHAVIORALLY_QUALIFIED"
    FORMALLY_QUALIFIED = "FORMALLY_QUALIFIED"


@dataclass(frozen=True, slots=True)
class RewritePrecondition:
    precondition_id: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {"precondition_id": self.precondition_id, "description": self.description}


@dataclass(frozen=True, slots=True)
class RewriteEvidence:
    evidence_class: str
    reference: str

    def as_dict(self) -> dict[str, str]:
        return {"evidence_class": self.evidence_class, "reference": self.reference}


@dataclass(frozen=True, slots=True)
class RewriteDefinition:
    rewrite_id: str
    version: str
    consumes: tuple[str, ...]
    produces: tuple[str, ...]
    preconditions: tuple[RewritePrecondition, ...]
    postconditions: tuple[str, ...]
    evidence: tuple[RewriteEvidence, ...]
    counterexamples: tuple[str, ...] = ()
    semantic_loss_delta: tuple[str, ...] = ()
    authority_ceiling: QualificationState = QualificationState.STRUCTURAL_ONLY
    provenance: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_REWRITE_DEFINITION_V1",
            "rewrite_id": self.rewrite_id,
            "version": self.version,
            "consumes": list(self.consumes),
            "produces": list(self.produces),
            "preconditions": [item.as_dict() for item in self.preconditions],
            "postconditions": list(self.postconditions),
            "evidence": [item.as_dict() for item in self.evidence],
            "counterexamples": list(self.counterexamples),
            "semantic_loss_delta": list(self.semantic_loss_delta),
            "authority_ceiling": self.authority_ceiling.value,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class RewriteApplication:
    rewrite_id: str
    rewrite_version: str
    definition_digest: str
    input_plan_digest: str
    output_plan_digest: str | None
    applicability: ApplicabilityState
    qualification: QualificationState
    evaluated_preconditions: tuple[tuple[str, str], ...]
    evaluated_postconditions: tuple[tuple[str, str], ...]
    evidence: tuple[str, ...] = ()
    semantic_loss_delta: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_REWRITE_APPLICATION_V1",
            "rewrite_id": self.rewrite_id,
            "rewrite_version": self.rewrite_version,
            "definition_digest": self.definition_digest,
            "input_plan_digest": self.input_plan_digest,
            "output_plan_digest": self.output_plan_digest,
            "applicability": self.applicability.value,
            "qualification": self.qualification.value,
            "evaluated_preconditions": [list(item) for item in self.evaluated_preconditions],
            "evaluated_postconditions": [list(item) for item in self.evaluated_postconditions],
            "evidence": list(self.evidence),
            "semantic_loss_delta": list(self.semantic_loss_delta),
        }


def rewrite_definition_digest(definition: RewriteDefinition) -> str:
    return canonical_digest(definition.as_dict())


def rewrite_application_digest(application: RewriteApplication) -> str:
    return canonical_digest(application.as_dict())
