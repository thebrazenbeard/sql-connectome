# Logical Semantic Plan V1

SQL Connectome derives a typed logical plan after static schema binding. The plan is distinct from the source-shaped SQLSemanticIR and does not replace source evidence.

The model uses bag semantics by default. Relational nodes carry output schemas and conservative semantic cardinality bounds. Fields preserve canonical type family, source type spelling, nullability state, stable identity, and provenance. Unknown facts remain UNKNOWN.

Current V1 construction covers relational SELECT structure including read, filter, project, limit, aggregate, set operation, outer-join null extension, and explicit nested-subquery scope evidence. It does not claim engine behavioral equivalence.

Substrait is treated as an interoperability receptor. Compatibility inspection reports EXACT, EXTENSION_REQUIRED, UNREPRESENTABLE, or UNKNOWN and never changes plan authority. V1 does not emit executable Substrait protobuf.
