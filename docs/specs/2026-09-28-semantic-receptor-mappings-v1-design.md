# Semantic Receptor Mappings V1

Status: APPROVED UNDER ROADMAP STANDING AUTHORIZATION

## Decision
Expose PRQL, Cypher, SPARQL, and dataframe-plan inputs only through explicit receptor mappings into subsets of the existing Logical Semantic Plan. A receptor describes representability; it does not parse arbitrary source text, invent SQL, or elevate semantic authority.

Each mapping binds source language, source construct, target logical operator, compatibility state, explicit semantic losses, evidence references, and receptor version. States are EXACT_SUBSET, LOSSY_SUBSET, UNSUPPORTED, and UNKNOWN.

V1 ships conservative mapping catalogs for relational PRQL/dataframe constructs, graph-pattern Cypher constructs, and SPARQL basic graph/filter/project constructs. Graph/RDF constructs without a faithful bag-relational representation remain LOSSY_SUBSET or UNSUPPORTED rather than being flattened silently.

Receptor results are deterministic evidence artifacts whose digests can be attached to Step 8 receipts. Step 10 does not claim executable source parsers or behavioral equivalence.