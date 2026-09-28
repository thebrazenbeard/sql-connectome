# Semantic Receptor Mappings V1 — Internal Hostile Review

Reviewed implementation lineage through c579d941953b46b09154a4311d2e2f3272b78fcd.

Attacks:
1. Parser overclaim: V1 maps declared constructs only; it does not parse PRQL, Cypher, SPARQL, or dataframe source programs.
2. Graph collapse: Cypher MATCH is LOSSY_SUBSET with explicit graph-pattern loss; variable-length paths are UNSUPPORTED.
3. RDF collapse: SPARQL basic graph patterns are LOSSY_SUBSET with RDF term/graph semantic loss; property paths are UNSUPPORTED.
4. Bag/set mismatch: no receptor mapping claims multiplicity conversion not represented by the target operator.
5. Unknown laundering: unmapped constructs return UNKNOWN plus NO_V1_RECEPTOR_MAPPING.
6. Authority laundering: artifacts state REPRESENTABILITY_EVIDENCE_ONLY and cannot authorize execution or establish behavioral equivalence.
7. Evidence substitution: evidence refs are bound into the deterministic mapping digest.

Finding: SURVIVES_NARROWED.

Claim ceiling: V1 establishes deterministic explicit receptor mappings into shared logical-plan subsets. It does not establish complete source-language parsing, executable compilation, graph/RDF semantic equivalence, or behavioral equivalence.

Independent-model review: NOT PERFORMED.
