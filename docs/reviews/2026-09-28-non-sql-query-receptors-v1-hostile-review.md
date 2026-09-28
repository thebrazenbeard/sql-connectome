# Non-SQL Query Receptors V1 — Internal Hostile Review

Reviewed implementation lineage through `a26145e0a9ff4673c262b1eaf4adee155df61461`.

## Attacks
1. Relationalization bias: only explicitly supported constructs map FULL; graph/RDF/dataframe semantics outside the shared subset become PARTIAL/UNSUPPORTED.
2. Cypher path loss: variable-length paths and OPTIONAL MATCH are explicit loss markers, never flattened into ordinary joins.
3. SPARQL semantics: entailment, named-graph/dataset semantics, and property paths are explicit unsupported boundaries.
4. Dataframe assumptions: index, order, and NA/null semantics have dedicated loss markers.
5. PRQL drift: source_version is bound in ExternalPlan; compiler extensions are unsupported unless explicitly mapped.
6. Unknown construct guessing: unknown constructs receive deterministic language-specific UNSUPPORTED markers.
7. Authority escalation: receptor mappings feed receipt evidence only; they do not carry execution authorization.
8. False logical-plan claim: PARTIAL/UNSUPPORTED mappings forcibly clear logical_plan_digest rather than advertising a complete mapped plan.
9. Provenance loss: source digest, version, and source provenance are bound into the external-plan digest.

## Finding
SURVIVES_NARROWED.

V1 establishes explicit receptor contracts and semantic boundaries. It does not yet include native PRQL/Cypher/SPARQL/dataframe parsers or full graph/RDF logical operators, and makes no claim that it does.

Independent-model review: NOT PERFORMED. This is internal hostile review only.
