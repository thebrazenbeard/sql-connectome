# Semantic Receptor Mappings V1 Implementation Plan

Goal: add explicit, deterministic PRQL/Cypher/SPARQL/dataframe-to-logical-subset mapping evidence.

1. Add receptor model, compatibility states, deterministic digest, and source-language enum.
2. Add conservative built-in mapping catalogs for PRQL, Cypher, SPARQL, and dataframe plans.
3. Add tests for exact relational subsets, lossy graph/RDF mappings, unsupported constructs, deterministic digests, and explicit losses.
4. Integrate receptor digests as Step 8 evidence refs without changing receipt authority.
5. Hostile review semantic collapse, graph/RDF flattening, bag/set mismatch, parser overclaim, and authority laundering. Require protected exact-head qualification before merge.

No unresolved V1 product decisions. Full source parsers and executable compilers are outside V1.