# Provider-Neutral Engine Validation Adapters V1 Design

**Status:** APPROVED design route
**Program step:** 3
**Canonical predecessor:** evidence-bearing coercion semantics on main at `72c31c9308f1914beb1f8a39df051b9903b8d63a`

## Goal

Generalize SQL Connectome target validation beyond PostgreSQL, DuckDB, and SQLite with one narrow provider-neutral validation contract and three independent engine implementations: MySQL, MariaDB, and Trino. This step extends validation semantics and engine evidence. It does not introduce the provider-neutral connectivity layer reserved for ordered step 7.

## Invariants

- `UNDERSTAND != BIND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`.
- Validation does not imply execution authorization.
- Engine identity, engine version, session/catalog identity, validation mechanism, error model, evidence, and qualification are independently represented per engine.
- MySQL and MariaDB are separate semantic/evidence adapters. Shared code is permitted only for mechanics whose meaning is demonstrably engine-neutral.
- Trino is the first distributed-family validation adapter.
- No adapter may infer behavioral equivalence from successful parsing, planning, or validation.
- Read-only SQL guard remains an upstream safety boundary, not proof of engine semantics.
- Receipts bind exact SQL digest, schema/catalog context digest, runtime identity digest, validation mode, status, and normalized error class/code where available.

## Provider-neutral contract

Introduce an engine-validation result contract containing contract/schema version, engine and adapter IDs, runtime identity/digest, SQL digest, supplied schema/catalog-context digest, status `PASS | FAIL | UNAVAILABLE`, validation mode, `query_executed`, established read-only/session facts, engine-native payload, normalized error envelope plus native fields, evidence ceiling, behavioral-equivalence ceiling, and deterministic receipt.

The neutral layer standardizes result shape and provenance. It does not standardize engine plan trees or native error taxonomies.

## MySQL adapter

Initial target is MySQL 8.4 behavior. Validation uses `EXPLAIN FORMAT=JSON` for admitted read-only statements. MySQL 8.4 has versioned JSON explain formats, so runtime identity records `explain_json_format_version` when available plus semantic session facts. The adapter never uses `EXPLAIN ANALYZE`.

The plan remains a MySQL-native opaque payload. V1 may establish that it is parseable JSON but does not normalize its optimizer tree across engines.

Runtime identity binds at least server/version, selected database, SQL mode, character set/collation facts relevant to semantics, time zone, and explain JSON format version when available.

## MariaDB adapter

Validation uses MariaDB `EXPLAIN FORMAT=JSON` independently from MySQL. MariaDB documents that its JSON explain output differs from MySQL, so no MySQL plan schema/parser is reused as semantic truth.

Runtime identity binds MariaDB server/version, database, SQL mode, character set/collation facts, time zone, and relevant optimizer/session facts available from the runtime. The adapter never substitutes `ANALYZE FORMAT=JSON`, because that executes the statement.

## Trino adapter

Validation uses `EXPLAIN (TYPE VALIDATE)`, which Trino documents as syntactic and semantic validation. Runtime identity binds Trino version plus catalog/schema/session identity. Connector/catalog identity is first-class because semantic validity can depend on connector behavior and catalog metadata.

No distributed plan is interpreted in this step.

## Connectivity boundary

V1 adapters accept injected connection/session factories or narrow protocol-compatible connection objects. They do not create a universal ADBC/JDBC/ODBC abstraction. Engine-specific driver packages may be optional extras. Tests use deterministic fake/protocol connections unless a real engine is explicitly available. Missing driver/runtime is `UNAVAILABLE`; it never silently falls back to another engine.

## Schema context

Existing DuckDB/SQLite validators synthesize ephemeral local schemas. Remote MySQL/MariaDB/Trino V1 adapters do not create or mutate remote schema during validation. Caller-supplied schema context is evidence for comparison/binding and receipts, not remote DDL.

## Errors and evidence

Neutral errors contain stable SQL Connectome categories only where justified plus native fields. MySQL/MariaDB preserve numeric error code, SQLSTATE, and message where exposed. Trino preserves native query/error name/type/code/message where exposed. Unknown native forms remain opaque.

Successful validation means the exact engine/runtime/session/catalog accepted the statement for the adapter validation mechanism. It does not establish cross-engine equivalence or successful execution.

## Hostile review requirements

Internal hostile review attacks accidental MySQL/MariaDB semantic coupling, omitted session identity, validation modes that execute, remote schema mutation, loss of native error/plan evidence, receipts omitting catalog/session identity, and fallback behavior that turns unavailable into another engine.

Independent-model hostile review is separate and exact-artifact-bound. Failures/timeouts are recorded, never promoted to a pass.

## Testing

Tests prove deterministic neutral receipts; independent MySQL/MariaDB adapter identities and evidence; MySQL explain-format version identity binding; MariaDB never calls ANALYZE; Trino uses `EXPLAIN (TYPE VALIDATE)`; validation does not execute the admitted query; no remote schema DDL is emitted; unavailable runtime is explicit; native errors survive normalization; receipts change with runtime/catalog/session identity; existing PostgreSQL/DuckDB/SQLite behavior remains compatible.

Real-engine qualification is independent per engine. One engine passing cannot qualify another.

## Non-goals

No ADBC/JDBC/ODBC abstraction (step 7), logical relational IR/Substrait (step 4), rewrite hyperedges (step 5), equivalence lab (step 6), cross-engine plan normalization, write execution, or MySQL/MariaDB semantic-family collapse.
