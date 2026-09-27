# Expression Semantic Registry

## Purpose

The expression semantic registry gives SQL Connectome stable semantic identities for a bounded set
of functions, aggregates, operators, control expressions, and conversions.

It is the first explicit source-controlled implementation of the `F` component in:

`SQLC(t) = (D, P, I, S, T, F, C, R, E, V, G, K)`

A registry entry identifies an operation. It does not claim that every dialect implements that
operation with identical runtime behavior.

## Stable identity

Examples include:

- `function.coalesce`;
- `function.least`;
- `aggregate.count`;
- `operator.div`;
- `operator.concat`;
- `conversion.cast`.

Each entry binds a semantic ID to the current normalized expression class plus:

- semantic kind;
- semantic family;
- argument-role names;
- known semantic-risk codes;
- optional notes.

The registry is immutable at runtime and has a canonical digest.

## IR binding

The parser projects the registry directly into the semantic IR.

For a registered expression node, IR attributes include:

- `semantic_state=REGISTERED`;
- `semantic_id`;
- `semantic_kind`;
- `semantic_family`;
- `semantic_risk_codes`.

For an unregistered function node, the IR preserves:

- `semantic_state=UNREGISTERED`;
- `semantic_id=null`;
- the source function name when available.

The IR envelope also carries the expression-registry schema and digest in
`semantic_extensions`, and the digest is repeated in parser provenance. This binds the meaning of
node-level semantic IDs to the exact source-controlled registry version used for parsing.

## Query-scoped inventory

The query inventory parses one declared-dialect statement and reports only function expressions and
registered operator/control/conversion classes that actually occur in that statement.

Known classes return `state=REGISTERED` plus their stable semantic ID.

Unknown function classes return:

```text
state = UNREGISTERED
semantic_id = null
```

An unregistered expression is not automatically unsupported. It means SQL Connectome has not yet
admitted a stable semantic identity for that expression.

## Risk linkage

Registry identity and semantic-risk analysis are deliberately separate.

For example:

`operator.div`

may link to:

- `DIVISION_TYPE_SEMANTICS`;
- `DIVISION_BY_ZERO_SEMANTICS`.

Likewise `function.least` and `function.greatest` link to
`LEAST_GREATEST_NULL_SEMANTICS`.

This allows a query to have a stable operation identity while translation fidelity is still capped
by dialect-specific behavior.

## Provenance

The registry manifest carries:

- source-controlled evidence basis;
- registry digest;
- entry count;
- behavioral-equivalence ceiling.

The query-scoped inventory additionally carries the current dialect-catalog digest.

Conformance snapshots bind the expression-registry digest independently of the dialect-catalog
digest so changes to semantic vocabulary become explicit drift.

## Claim ceiling

A semantic ID establishes source-controlled operation identity only.

It does not establish:

- equal NULL behavior;
- equal type/coercion behavior;
- equal error behavior;
- equal ordering/collation behavior;
- target-engine acceptance;
- cross-engine behavioral equivalence;
- execution authority.

The core invariant remains:

`UNDERSTAND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`
