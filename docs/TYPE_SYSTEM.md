# SQL Connectome Type System

## Purpose

The type system implements the `T` component of:

`SQLC(t) = (D, P, I, S, T, F, C, R, E, V, G, K)`

It provides canonical semantic type families, dialect coercion evidence, explicit type-projection
fidelity, and type identity embedded directly in semantic IR.

## Canonical families

SQL Connectome normalizes admitted type names into bounded semantic families including:

- NULL and BOOLEAN;
- INTEGER, DECIMAL, and FLOAT;
- STRING and BINARY;
- DATE, TIME, TIMESTAMP, and INTERVAL;
- JSON;
- ARRAY, MAP, and STRUCT;
- VARIANT;
- UUID;
- GEOSPATIAL;
- VECTOR;
- OTHER.

`OTHER` is explicit uncertainty. It is not treated as unsupported.

## Dialect coercion graph

For each admitted parser dialect, SQL Connectome derives a graph from the pinned SQLGlot
`COERCES_TO` metadata.

Each edge records:

- source and target dialect type names;
- source and target canonical families;
- an evidence mode;
- a conservative fidelity/risk class.

The graph has the evidence ceiling `DEPENDENCY_METADATA`.

A missing edge means `UNKNOWN_NOT_UNSUPPORTED`. SQL Connectome does not turn incomplete upstream
metadata into a negative capability claim.

## Explicit type semantics in IR

When parsing SQL, each explicit SQLGlot `DataType` node receives IR attributes:

```text
type_semantic_state = EXPLICIT
type_dialect_name
type_canonical_family
type_source_sql
type_parameters
type_evidence_basis = PARSED_EXPLICIT_TYPE
```

This is parse-time evidence only. It does not claim that an unbound column has that runtime type.

The IR envelope binds the source-dialect type graph with:

```text
source_type_graph_schema = SQL_CONNECTOME_TYPE_GRAPH_V1
source_type_graph_digest
type_semantic_coverage = EXPLICIT_TYPES_ONLY
```

The same digest is included in IR provenance and in the conformance snapshot. Consumers can
therefore cross-bind a node-level canonical type identity to the exact dialect type/coercion graph
used when the IR was produced.

## Translation fidelity

Explicit type projections are evaluated separately from capability and function/operator semantics.

The translation result preserves independent fidelity components:

```text
capability
expression_semantics
types
```

The combined translation ceiling is the worst of those components.

Known representation fallbacks such as VARIANT-to-JSON or STRUCT-to-JSON remain `LOSSY` even when
target SQL can be generated, because source typing/coercion semantics may not survive.

## Static binding overlay

Schema binding does not rewrite the parse-time IR in place. It produces a separate bound graph from
the qualified and SQLGlot-annotated AST.

Each bound node records static type state and canonical family where available. Column nodes also
record their qualified table/column identity. The bound IR is cross-bound to both the source IR
digest and the schema-context digest.

This makes parse identity and binding evidence independently reconstructible and allows star
expansion or qualification to change bound-graph shape without pretending the original parse graph
was mutated.

Unknown projection-result types contribute to the binding's `PARTIAL` annotation ceiling even when
all referenced columns have known schema types.

## Separation from schema binding

Parse-time explicit type identity and schema-bound inferred type information are distinct.

`parse_sql_text` may identify the meaning of an explicit type token.

`bind_sql_text` may later use a supplied schema to qualify columns, expand stars, and infer or
annotate expression types.

Neither state by itself establishes target-engine acceptance or cross-engine behavioral equivalence.

## Claim ceiling

The type layer preserves:

`PARSE_TYPE_IDENTITY != SCHEMA_BINDING != ENGINE_TYPE_BEHAVIOR != BEHAVIORAL_EQUIVALENCE`

The broader project invariant remains:

`UNDERSTAND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`
