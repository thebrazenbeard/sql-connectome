from sql_connectome.receptors import (
    ReceptorLanguage,
    ReceptorState,
    map_receptor_construct,
)


def test_prql_relational_subset_maps_exactly() -> None:
    result = map_receptor_construct(ReceptorLanguage.PRQL, "filter")
    assert result.target_operator == "FILTER"
    assert result.state is ReceptorState.EXACT_SUBSET
    assert result.semantic_losses == ()


def test_dataframe_groupby_maps_to_aggregate_subset() -> None:
    result = map_receptor_construct(ReceptorLanguage.DATAFRAME, "groupby")
    assert result.target_operator == "AGGREGATE"
    assert result.state is ReceptorState.EXACT_SUBSET


def test_cypher_graph_pattern_does_not_silently_flatten() -> None:
    result = map_receptor_construct(ReceptorLanguage.CYPHER, "match")
    assert result.state is ReceptorState.LOSSY_SUBSET
    assert result.semantic_losses == ("GRAPH_PATTERN_TO_RELATIONAL_JOIN_LOSS",)


def test_sparql_property_path_is_explicitly_unsupported() -> None:
    result = map_receptor_construct(ReceptorLanguage.SPARQL, "property_path")
    assert result.target_operator is None
    assert result.state is ReceptorState.UNSUPPORTED


def test_unknown_construct_remains_unknown() -> None:
    result = map_receptor_construct(ReceptorLanguage.PRQL, "derive_magic")
    assert result.state is ReceptorState.UNKNOWN
    assert result.semantic_losses == ("NO_V1_RECEPTOR_MAPPING",)


def test_receptor_digest_binds_language_construct_and_evidence() -> None:
    first = map_receptor_construct(ReceptorLanguage.PRQL, "filter", evidence_refs=("spec:1",))
    same = map_receptor_construct(ReceptorLanguage.PRQL, "filter", evidence_refs=("spec:1",))
    other = map_receptor_construct(ReceptorLanguage.PRQL, "filter", evidence_refs=("spec:2",))
    assert first.digest() == same.digest()
    assert first.digest() != other.digest()
    assert first.as_dict()["authority"] == "REPRESENTABILITY_EVIDENCE_ONLY"
