# Logical Semantic Plan V1 Design

## Decision

SQL Connectome will add a Connectome-native typed bag-relational DAG above the existing source-shaped `SQLSemanticIR` and static binding layer. The existing IR remains source evidence; the logical plan is a distinct derived semantic artifact with its own digest, provenance, coverage, and loss state.

Substrait is an interoperability receptor/export target only. It does not define Connectome's internal semantics.

## Core model

A `LogicalPlan` is an immutable DAG with one or more roots and stable node/scope identifiers. V1 relational operators are `READ`, `VALUES`, `PROJECT`, `FILTER`, `JOIN`, `AGGREGATE`, `WINDOW`, `SET_OP`, `SORT`, `LIMIT`, `DISTINCT`, `LATERAL`, and `SUBQUERY`. Unsupported source constructs remain explicit as loss/unrepresentable evidence; they are never silently dropped.

Every relational node owns an output `LogicalSchema`. Each field records stable field identity, display name, canonical type family, source type spelling, nullability state, and provenance. Nullability is `NULLABLE | NON_NULL | UNKNOWN`; UNKNOWN is preserved rather than guessed.

Expressions are separate immutable typed nodes. Field references bind stable field and scope IDs. Correlated references additionally carry an outer scope ID; they are not encoded as parser-tree depth. Expression typing records canonical family, source spelling where known, nullability, and evidence basis.

Cardinality is semantic metadata, not an optimizer estimate. V1 uses conservative bounds `minimum: int | None`, `maximum: int | None`, plus certainty `PROVEN | DERIVED | UNKNOWN`. Operators may tighten bounds only from semantics (for example LIMIT); no statistics-derived row-count estimate is admitted.

Bag semantics are the default. Operators that change multiplicity, including DISTINCT and set operations, state that explicitly.

## Derivation boundary

`logical_plan_from_bound_sql(...)` consumes the qualified/typed expression produced by static binding plus the source/bound IR digests. It never reparses into a second dialect model and never mutates source or bound IR. V1 admits relational SELECT queries supported by the binder; unsupported constructs return explicit coverage/loss rather than invented semantics.

## Substrait boundary

A `SubstraitCompatibility` inspection maps Connectome logical operators/types/references to Substrait concepts without making Substrait a dependency of plan construction. Results are `EXACT | EXTENSION_REQUIRED | UNREPRESENTABLE | UNKNOWN`, with per-feature reasons. No compatibility result may improve the authority of the underlying SQL binding or engine evidence.

## Evidence and receipts

The logical-plan artifact binds source IR digest, bound IR digest, schema-context digest, logical-plan digest, derivation version, and loss/coverage. Deterministic serialization is mandatory. Identical bound input and derivation version must produce identical plan digests.

## Hostile-review targets

Review must attack: accidental set semantics, nullability overclaim, alias/field identity collisions, correlated-scope capture, join null-extension, aggregate cardinality, set-operation schema alignment, unstable IDs/digests, and Substrait semantic collapse.

## Qualification ceiling

V1 qualification establishes deterministic construction and focused semantic invariants against controlled fixtures. It does not establish SQL equivalence, engine behavioral equivalence, or formal proof. Those remain later conformance/equivalence work.
