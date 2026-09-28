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


from .logical_plan import LogicalPlan, logical_plan_digest


REDUNDANT_PROJECT_ELIMINATION_V1 = RewriteDefinition(
    rewrite_id="redundant-project-elimination",
    version="1",
    consumes=("PROJECT", "INPUT_RELATION"),
    produces=("INPUT_RELATION",),
    preconditions=(
        RewritePrecondition(
            "PROJECT_KIND",
            "target relation must be PROJECT",
        ),
        RewritePrecondition(
            "SINGLE_INPUT",
            "project must have exactly one input relation",
        ),
        RewritePrecondition(
            "IDENTICAL_OUTPUT_SCHEMA",
            "project and input schemas must match field-for-field",
        ),
        RewritePrecondition(
            "IDENTICAL_RELATION_PROPERTIES",
            "scope, multiplicity, and cardinality must match",
        ),
    ),
    postconditions=("ROOT_OR_INPUT_REFERENCES_REPLACED_WITH_PROJECT_INPUT",),
    evidence=(
        RewriteEvidence(
            "static-structural-rule",
            "docs/specs/2026-09-28-governed-semantic-rewrite-hyperedges-v1-design.md",
        ),
    ),
    counterexamples=(
        "projection reorders fields",
        "projection changes field identity, type, nullability, provenance, multiplicity, or cardinality",
    ),
    semantic_loss_delta=("REDUNDANT_PROJECT_ELIMINATION_STRUCTURAL_V1",),
    authority_ceiling=QualificationState.STRUCTURAL_ONLY,
    provenance=("sql-connectome-step-5",),
)


def _application(
    definition: RewriteDefinition,
    plan: LogicalPlan,
    *,
    applicability: ApplicabilityState,
    preconditions: tuple[tuple[str, str], ...],
    output: LogicalPlan | None = None,
    postconditions: tuple[tuple[str, str], ...] = (),
    evidence: tuple[str, ...] = (),
) -> RewriteApplication:
    return RewriteApplication(
        rewrite_id=definition.rewrite_id,
        rewrite_version=definition.version,
        definition_digest=rewrite_definition_digest(definition),
        input_plan_digest=logical_plan_digest(plan),
        output_plan_digest=logical_plan_digest(output) if output is not None else None,
        applicability=applicability,
        qualification=QualificationState.STRUCTURAL_ONLY,
        evaluated_preconditions=preconditions,
        evaluated_postconditions=postconditions,
        evidence=evidence,
        semantic_loss_delta=definition.semantic_loss_delta if output is not None else (),
    )


def apply_redundant_project_elimination(
    plan: LogicalPlan,
    relation_id: str,
) -> tuple[LogicalPlan, RewriteApplication]:
    plan.validate()
    definition = REDUNDANT_PROJECT_ELIMINATION_V1
    relations = {relation.relation_id: relation for relation in plan.relations}
    project = relations.get(relation_id)
    checks: list[tuple[str, str]] = []

    if project is None:
        checks.append(("PROJECT_KIND", "UNRESOLVED"))
        return plan, _application(
            definition,
            plan,
            applicability=ApplicabilityState.UNRESOLVED,
            preconditions=tuple(checks),
        )
    if project.kind != "PROJECT":
        checks.append(("PROJECT_KIND", "FAIL"))
        return plan, _application(
            definition,
            plan,
            applicability=ApplicabilityState.NOT_APPLICABLE,
            preconditions=tuple(checks),
        )
    checks.append(("PROJECT_KIND", "PASS"))

    if len(project.inputs) != 1:
        checks.append(("SINGLE_INPUT", "FAIL"))
        return plan, _application(
            definition,
            plan,
            applicability=ApplicabilityState.NOT_APPLICABLE,
            preconditions=tuple(checks),
        )
    checks.append(("SINGLE_INPUT", "PASS"))

    input_relation = relations.get(project.inputs[0])
    if input_relation is None:
        checks.append(("IDENTICAL_OUTPUT_SCHEMA", "UNRESOLVED"))
        return plan, _application(
            definition,
            plan,
            applicability=ApplicabilityState.UNRESOLVED,
            preconditions=tuple(checks),
        )

    if project.output_schema != input_relation.output_schema:
        checks.append(("IDENTICAL_OUTPUT_SCHEMA", "FAIL"))
        return plan, _application(
            definition,
            plan,
            applicability=ApplicabilityState.NOT_APPLICABLE,
            preconditions=tuple(checks),
        )
    checks.append(("IDENTICAL_OUTPUT_SCHEMA", "PASS"))

    same_properties = (
        project.scope_id == input_relation.scope_id
        and project.multiplicity == input_relation.multiplicity
        and project.cardinality == input_relation.cardinality
    )
    if not same_properties:
        checks.append(("IDENTICAL_RELATION_PROPERTIES", "FAIL"))
        return plan, _application(
            definition,
            plan,
            applicability=ApplicabilityState.NOT_APPLICABLE,
            preconditions=tuple(checks),
        )
    checks.append(("IDENTICAL_RELATION_PROPERTIES", "PASS"))

    rewritten_relations = []
    for relation in plan.relations:
        if relation.relation_id == project.relation_id:
            continue
        if project.relation_id in relation.inputs:
            relation = type(relation)(
                relation.relation_id,
                relation.kind,
                relation.output_schema,
                relation.cardinality,
                tuple(
                    input_relation.relation_id if item == project.relation_id else item
                    for item in relation.inputs
                ),
                relation.scope_id,
                relation.multiplicity,
            )
        rewritten_relations.append(relation)

    output = LogicalPlan(
        roots=tuple(
            input_relation.relation_id if root == project.relation_id else root
            for root in plan.roots
        ),
        relations=tuple(rewritten_relations),
        source_ir_digest=plan.source_ir_digest,
        bound_ir_digest=plan.bound_ir_digest,
        schema_digest=plan.schema_digest,
        expressions=plan.expressions,
        losses=(*plan.losses, *definition.semantic_loss_delta),
    )
    output.validate()
    post = (("ROOT_OR_INPUT_REFERENCES_REPLACED_WITH_PROJECT_INPUT", "PASS"),)
    return output, _application(
        definition,
        plan,
        applicability=ApplicabilityState.APPLICABLE,
        preconditions=tuple(checks),
        output=output,
        postconditions=post,
        evidence=("deterministic-structural-identity-check",),
    )
