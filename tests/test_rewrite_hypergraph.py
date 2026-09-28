from sql_connectome.connectome.logical_plan import (
    CardinalityBounds,
    LogicalField,
    LogicalPlan,
    LogicalRelation,
    LogicalSchema,
    LogicalType,
    Multiplicity,
    Nullability,
)
from sql_connectome.connectome.rewrite_hypergraph import (
    ApplicabilityState,
    QualificationState,
    RewriteApplication,
    RewriteDefinition,
    RewriteEvidence,
    RewritePrecondition,
    rewrite_definition_digest,
)


def _plan() -> LogicalPlan:
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
        schema,
        CardinalityBounds(minimum=0, maximum=None),
        inputs=("relation:read:0",),
        scope_id="scope:0",
        multiplicity=Multiplicity.BAG,
    )
    return LogicalPlan(
        roots=("relation:project:0",),
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
            RewritePrecondition("IDENTICAL_OUTPUT_SCHEMA", "project and input schemas must match"),
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
