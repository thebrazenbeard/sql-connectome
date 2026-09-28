from sql_connectome.connectome.logical_plan import (
    CardinalityBounds,
    LogicalField,
    LogicalPlan,
    LogicalRelation,
    LogicalSchema,
    LogicalType,
    Multiplicity,
    Nullability,
    logical_plan_digest,
)
from sql_connectome.connectome.rewrite_hypergraph import (
    ApplicabilityState,
    QualificationState,
    RewriteApplication,
    RewriteDefinition,
    RewriteEvidence,
    RewritePrecondition,
    apply_redundant_project_elimination,
    rewrite_definition_digest,
)


def _plan(*, project_schema: LogicalSchema | None = None) -> LogicalPlan:
    schema = LogicalSchema(
        (
            LogicalField(
                "field:a",
                "a",
                LogicalType("INTEGER", "INT"),
                Nullability.NON_NULL,
                ("source:a",),
            ),
        )
    )
    read = LogicalRelation(
        "relation:read:0",
        "READ",
        schema,
        CardinalityBounds(minimum=0, maximum=None),
        scope_id="scope:0",
        multiplicity=Multiplicity.BAG,
    )
    project = LogicalRelation(
        "relation:project:0",
        "PROJECT",
        project_schema or schema,
        read.cardinality,
        inputs=(read.relation_id,),
        scope_id=read.scope_id,
        multiplicity=read.multiplicity,
    )
    return LogicalPlan(
        roots=(project.relation_id,),
        relations=(read, project),
        source_ir_digest="source",
        bound_ir_digest="bound",
        schema_digest="schema",
        losses=("EXISTING_LOSS",),
    )


def test_rewrite_definition_digest_is_deterministic_and_evidence_bearing() -> None:
    definition = RewriteDefinition(
        rewrite_id="redundant-project-elimination",
        version="1",
        consumes=("relation:project:0", "relation:read:0"),
        produces=("relation:read:0",),
        preconditions=(
            RewritePrecondition(
                "IDENTICAL_OUTPUT_SCHEMA",
                "project and input schemas must match",
            ),
        ),
        postconditions=("ROOT_REPLACED_WITH_INPUT",),
        evidence=(RewriteEvidence("design", "docs/specs/example"),),
        counterexamples=("projection reorders fields",),
        semantic_loss_delta=("REWRITE_APPLIED_STRUCTURALLY",),
        authority_ceiling=QualificationState.STRUCTURAL_ONLY,
        provenance=("test",),
    )
    assert rewrite_definition_digest(definition) == rewrite_definition_digest(definition)
    assert definition.counterexamples == ("projection reorders fields",)


def test_application_state_does_not_imply_behavioral_equivalence() -> None:
    application = RewriteApplication(
        rewrite_id="redundant-project-elimination",
        rewrite_version="1",
        definition_digest="definition",
        input_plan_digest="input",
        output_plan_digest="output",
        applicability=ApplicabilityState.APPLICABLE,
        qualification=QualificationState.STRUCTURAL_ONLY,
        evaluated_preconditions=(("IDENTICAL_OUTPUT_SCHEMA", "PASS"),),
        evaluated_postconditions=(("ROOT_REPLACED_WITH_INPUT", "PASS"),),
        evidence=("static-identity-check",),
        semantic_loss_delta=("REWRITE_APPLIED_STRUCTURALLY",),
    )
    assert application.qualification is QualificationState.STRUCTURAL_ONLY


def test_redundant_project_rewrite_preserves_boundaries_and_appends_loss() -> None:
    plan = _plan()
    output, receipt = apply_redundant_project_elimination(plan, "relation:project:0")
    assert receipt.applicability is ApplicabilityState.APPLICABLE
    assert receipt.qualification is QualificationState.STRUCTURAL_ONLY
    assert output.source_ir_digest == plan.source_ir_digest
    assert output.bound_ir_digest == plan.bound_ir_digest
    assert output.schema_digest == plan.schema_digest
    assert output.roots == ("relation:read:0",)
    assert output.losses[:1] == ("EXISTING_LOSS",)
    assert output.losses[-1] == "REDUNDANT_PROJECT_ELIMINATION_STRUCTURAL_V1"
    assert receipt.input_plan_digest == logical_plan_digest(plan)
    assert receipt.output_plan_digest == logical_plan_digest(output)


def test_redundant_project_rewrite_refuses_schema_divergence() -> None:
    divergent = LogicalSchema(
        (
            LogicalField(
                "field:a",
                "renamed",
                LogicalType("INTEGER", "INT"),
                Nullability.NON_NULL,
                ("source:a",),
            ),
        )
    )
    plan = _plan(project_schema=divergent)
    output, receipt = apply_redundant_project_elimination(plan, "relation:project:0")
    assert output is plan
    assert receipt.applicability is ApplicabilityState.NOT_APPLICABLE
    assert receipt.output_plan_digest is None
