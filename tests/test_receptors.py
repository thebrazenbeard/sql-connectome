from sql_connectome.cross_bound_receipts import TransitionKind, make_cross_bound_receipt
from sql_connectome.receptor_mapping import map_external_plan
from sql_connectome.receptors import ExternalPlan, MappingState, ReceptorLanguage


def _plan(language, constructs):
    return ExternalPlan(language, "1", f"source:{language.value}", constructs, ("user-plan",))


def test_prql_relational_subset_maps_fully() -> None:
    mapping = map_external_plan(
        _plan(ReceptorLanguage.PRQL, ("SCAN", "FILTER", "PROJECT")),
        logical_plan_digest="logical",
    )
    assert mapping.state is MappingState.FULL
    assert mapping.logical_plan_digest == "logical"


def test_cypher_path_semantics_are_not_guessed() -> None:
    mapping = map_external_plan(
        _plan(ReceptorLanguage.CYPHER, ("SCAN", "PROJECT", "VARIABLE_LENGTH_PATH")),
        logical_plan_digest="should-not-survive",
    )
    assert mapping.state is MappingState.PARTIAL
    assert mapping.logical_plan_digest is None
    assert "CYPHER_PATH_SEMANTICS_UNMODELED_V1" in mapping.semantic_losses


def test_sparql_entailment_is_explicit_loss_boundary() -> None:
    mapping = map_external_plan(_plan(ReceptorLanguage.SPARQL, ("ENTAILMENT",)))
    assert mapping.state is MappingState.UNSUPPORTED
    assert mapping.semantic_losses == ("SPARQL_ENTAILMENT_UNMODELED_V1",)


def test_dataframe_index_order_null_semantics_are_explicit() -> None:
    mapping = map_external_plan(
        _plan(ReceptorLanguage.DATAFRAME, ("SCAN", "INDEX", "ORDER", "NA_POLICY"))
    )
    assert mapping.state is MappingState.PARTIAL
    assert len(mapping.semantic_losses) == 3


def test_mapping_evidence_can_feed_cross_bound_receipt_without_authority_escalation() -> None:
    mapping = map_external_plan(_plan(ReceptorLanguage.PRQL, ("SCAN", "PROJECT")))
    receipt = make_cross_bound_receipt(
        TransitionKind.UNDERSTAND,
        input_digests=("external",),
        output_digests=(mapping.digest(),),
        evidence_refs=(mapping.digest(),),
        semantic_loss_delta=mapping.semantic_losses,
    )
    assert receipt.authority.authorization_receipt is None
    assert receipt.evidence_refs == (mapping.digest(),)
