# SQL Connectome Semantic Model

## Design source

This executable architecture promotes the concepts captured on the repository branch
`sql-connectome-idea` into source-controlled runtime structures. The design branch remains
useful historical/design evidence; this document defines how those ideas map into the current
implementation slice.

## Core model

SQL Connectome is not a universal keyword parser and not a lowest-common-denominator SQL AST.

The conceptual state is:

`SQLC(t) = (D, P, I, S, T, F, C, R, E, V, G, K)`

Where:

- `D`: dialect and version space;
- `P`: parsers and tokenizers;
- `I`: universal semantic intermediate representation;
- `S`: schema, catalog, and session context;
- `T`: type and coercion systems;
- `F`: functions, operators, and procedures;
- `C`: capability graph;
- `R`: rewrite and transformation knowledge;
- `E`: execution adapters;
- `V`: validation;
- `G`: authority and effect governance;
- `K`: provenance, uncertainty, and semantic-loss state.

The current code implements executable portions of `D`, `P`, `I`, `S`, `T`, `F`, `C`, `R`, `E`, `V`, `G`, and `K`. Coverage remains intentionally partial and evidence-bounded. PostgreSQL is retained as the first connected execution/governance substrate rather than defining the scope of the whole project.

## Dialect genomes and governed admission

A dialect genome is a version-aware capability bundle, not merely a name.

The default registry is deliberately conservative. A listed dialect does not imply complete grammar
or conformance coverage. Capabilities are admitted as explicit facts needed by tested translation
rules and grow under evidence. Higher-coverage genomes coexist with baseline SQLGlot-backed genomes
whose admitted semantics may be limited to relational SELECT behavior.

Executable admission is bound by the immutable `ConnectomeCatalog`. The source-controlled
`DEFAULT_CATALOG` combines:

- canonical dialect genomes and aliases;
- parser-adapter bindings;
- admitted rewrite rules.

Catalog construction rejects non-normalized canonical IDs, ID/genome mismatches, alias collisions,
orphan parser adapters, and empty parser adapters. `admit_dialect(...)` is copy-on-write: extending
a catalog produces a new validated catalog rather than mutating the trusted source catalog.

Library semantic entrypoints can consume an explicitly supplied catalog for parsing, static binding,
expression/type inspection, dialect probing, inventory, and transpilation. The REST/MCP runtime
surfaces intentionally use the source-controlled default. Installed parser/dialect plugins are not
auto-discovered or auto-admitted; installation does not establish semantic authority, engine
validation, execution authority, or permission to mutate the runtime.

Conformance snapshots bind the default catalog with a canonical digest. A future dialect can
therefore be attached by adding a genome, parser adapter, semantic connections, rewrite evidence,
and qualification without modifying one monolithic universal grammar.

## Semantic dimensions

The model preserves multiple overlapping dimensions:

- relational;
- document/JSON;
- nested;
- graph;
- vector;
- geospatial;
- temporal;
- streaming;
- analytical;
- transactional;
- procedural;
- administrative;
- federated.

A statement may inhabit several dimensions at once.

## Universal semantic IR

`SQLSemanticIR` is graph-shaped. It stores typed nodes and typed edges plus capabilities,
dimensions, provenance, side effects, extensions, and translation loss.

Dialect-specific semantics are allowed to survive in the IR. The system must not erase a source
feature merely because a target cannot express it.

The current SQL text pipeline parses bounded, declared-dialect input into that graph, validates
source capability admission, and keeps parser acceptance distinct from target-engine validation.

## Translation fidelity

Translation is not boolean.

- `EXACT`: the target natively supports all required admitted capabilities at the capability-planning layer.
- `CONSTRUCTIVE`: missing syntax can be reconstructed from target capabilities without a known
  semantic loss at the capability-planning layer.
- `LOSSY`: a rewrite exists but known semantics may not survive exactly.
- `UNREPRESENTABLE`: at least one required capability has neither native support nor an admitted
  rewrite.

The planner fails closed on unresolved target capabilities and on capabilities not admitted by the declared source dialect. `EXACT` is not a claim of cross-engine behavioral equivalence; behavioral equivalence remains `NOT_ESTABLISHED` until binding, typing, target validation, and where needed differential execution prove it.

Examples in the bootstrap rule set:

- BigQuery/Snowflake-style `QUALIFY` can be planned through window functions plus a derived
  relation on targets such as PostgreSQL: `CONSTRUCTIVE`.
- T-SQL `APPLY` can be planned through a lateral relation where target semantics permit:
  `CONSTRUCTIVE`.
- Oracle `CONNECT BY` can be approximated through recursive CTE capability, but Oracle-specific
  pseudocolumn/cycle/sibling-order behavior prevents an exact blanket claim: `LOSSY`.
- Snowflake `VARIANT` may map to JSON representation, but source typing/coercion semantics are
  not guaranteed to survive: `LOSSY`.

## Separation of concerns

The following are intentionally distinct:

`UNDERSTAND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`

Recognizing a dialect does not establish that it can be translated.
Producing target SQL does not establish that the target engine accepts it.
Successful validation does not grant execution authority.
Read execution authority does not grant write authority.

## Runtime path

The intended mature path is:

```text
SQL text
  -> dialect candidate ensemble
  -> parse candidates
  -> schema/session binding
  -> semantic SQL IR
  -> capability/effect annotation
  -> target capability matching
  -> rewrite coalition
  -> target-dialect IR
  -> SQL generation
  -> static validation
  -> target prepare/EXPLAIN/sandbox validation
  -> authorized execution
  -> normalized result + provenance
```

The current implementation now includes a SQLGlot-backed text adapter that parses declared source
dialects into the semantic IR, performs planner-gated transpilation, and reparses generated target
SQL. SQLGlot remains a peripheral parser/transpiler rather than semantic authority. Successful
source parse, generation, and target reparse still do not establish cross-engine behavioral
equivalence.

## Unknown dialects

The long-term design supports partial interpretation of unknown dialects. Known lexical,
structural, function, type, and capability signals may bind to existing semantic nodes while
unrecognized constructs remain explicit unknowns.

The system should prefer partial, provenance-bearing understanding over falsely forcing an unknown
dialect into the nearest known family.


## Dialect probing

When the source dialect is unknown, SQL Connectome can probe all currently registered parser
adapters. The probe is deliberately evidentiary rather than identificatory.

Each candidate is informed by:

- whether the dialect parser accepts exactly one statement under strict parse errors;
- whether the current dialect genome admits the semantic capabilities observed by the text layer;
- narrowly scoped dialect markers such as T-SQL `TOP/APPLY`, Snowflake `VARIANT`,
  Oracle `CONNECT BY`, ClickHouse `ENGINE`, or Redshift distribution keys.

The probe returns a score and the evidence that produced it. It does not return invented
probabilities, and `identity_proof` is always false. Equal top scores remain explicitly
`ambiguous`.

Parser coverage is intentionally broader than semantic capability coverage. A dialect may therefore
be a valid parse candidate while reporting `semantic_admission=PARTIAL`; that state is a prompt to
extend the genome under evidence and tests, not permission to assume compatibility.


## Schema and type binding

Parsing establishes structure, not what an identifier resolves to. SQL Connectome therefore treats
schema binding as a separate state.

`bind_sql_text` accepts an explicit schema context and may:

- qualify table and column references;
- expand stars from known table columns;
- annotate column and projection types;
- return unresolved/unknown type counts;
- bind the result to a canonical schema digest.

The result is labeled `STATIC_BOUND`. It does not imply that the target engine has been contacted
or that SQLGlot's qualification/type inference is infallible. Engine validation remains
`NOT_RUN`, behavioral equivalence remains `NOT_ESTABLISHED`, and the authority ceiling is
`STATIC_ANALYSIS_ONLY`.

This separation allows future engine-backed prepare/EXPLAIN validation or differential execution to
strengthen the evidence without retroactively redefining a parser/optimizer result as runtime truth.


## Target-engine validation

Static parsing and schema binding can now be strengthened for the PostgreSQL execution substrate by
asking the connected engine to plan a guarded SELECT with `EXPLAIN (FORMAT JSON)`.

The PostgreSQL V1 validator:

- accepts only the existing single-SELECT read shape;
- opens a PostgreSQL READ ONLY transaction;
- applies the configured statement timeout;
- uses EXPLAIN without ANALYZE, so the query plan is requested but the query result is not executed;
- records PASS or FAIL against the exact runtime identity and SQL digest;
- preserves PostgreSQL SQLSTATE on planning/binding failures;
- emits a canonical validation receipt.

A PASS means the connected PostgreSQL runtime accepted and planned that statement under the current
catalog/session context. It is stronger evidence than target-parser acceptance, but it still does
not prove result equivalence with another engine, performance characteristics, or successful query
execution.


## End-to-end PostgreSQL translation qualification

The PostgreSQL qualification pipeline composes previously separate evidence states without
collapsing them.

For a declared source dialect it performs:

```text
source SQL
  -> strict bounded source parse
  -> source capability admission
  -> translation fidelity plan
  -> strict PostgreSQL generation
  -> strict PostgreSQL target parse
  -> live PostgreSQL read-only EXPLAIN
  -> qualification receipt
```

A qualification `PASS` means the exact generated PostgreSQL was accepted and planned by the exact
connected PostgreSQL runtime recorded in the receipt. A `FAIL` may therefore coexist with a
successful translation and target parse when the real target catalog cannot bind the generated SQL.

The qualification still reports `behavioral_equivalence=NOT_ESTABLISHED` and
`query_executed=false`. Planning acceptance does not prove source/target result equality.


## Expression-level semantic conformance

Capability support is necessary but not sufficient for translation fidelity. Two dialects can both
accept the same function or operator while assigning it different runtime meaning.

SQL Connectome therefore evaluates expression families that are actually present in the source AST
against semantic flags published by the pinned SQLGlot dialect implementation.

The V1 expression-semantic layer inventories:

- functions;
- operators;
- explicitly represented data types.

It currently admits conditional semantic-risk rules for:

- LEAST/GREATEST NULL handling;
- integer/type-sensitive division behavior;
- division-by-zero behavior;
- CONCAT NULL handling;
- CONCAT argument-type strictness;
- positional index base offsets;
- two-argument LOG argument order.

A semantic risk does not claim that a result is definitely different for every input. It states the
condition under which the source and target dialect behavior diverges. Because that condition may be
satisfied at runtime, the translation receives a LOSSY semantic fidelity ceiling unless the caller
explicitly opts in.

This means a translation may simultaneously report:

```text
capability_fidelity = EXACT
expression_semantic_fidelity = LOSSY
combined_fidelity = LOSSY
```

That is intentional. Feature availability is not semantic equivalence.


## Query-scoped expression contracts

SQL Connectome can now inspect the expression classes actually present in a query and expose their
dialect-bound structural/type contracts without serializing SQLGlot's internal callables.

For each distinct expression class present, the contract surface records:

- semantic kind: function, operator, type, or other expression;
- normalized expression/function name;
- required and optional child arguments;
- whether the expression accepts a variable-length argument list;
- whether SQLGlot models its type as a fixed return type, inferred by an annotator, or unspecified;
- the fixed return type when one is declared;
- whether dialect expression metadata exists;
- occurrence count in the current query.

The same response exposes the dialect's declared type-coercion graph. This remains dependency
evidence from the pinned SQLGlot version, not independent engine proof. Runtime binding and
target-engine validation remain separate states.


## Canonical type and coercion graph

The V1 type layer makes `T` explicit rather than treating types as incidental parser metadata.

It defines canonical semantic families including boolean, integer, decimal, floating-point, string,
binary, temporal, JSON, array/map/struct, variant, UUID, geospatial, vector, and an explicit
`OTHER` bucket.

For each admitted parser dialect, SQL Connectome can expose:

- dialect type names observed in SQLGlot's coercion metadata;
- their canonical semantic families;
- implicit coercion edges;
- a conservative edge classification such as same-family, numeric widening, temporal widening,
  binary-float precision risk, or cross-family coercion;
- the exact pinned SQLGlot version that supplied the dependency evidence.

A missing coercion edge means `UNKNOWN_NOT_UNSUPPORTED`. SQL Connectome does not turn incomplete
dependency metadata into a negative capability claim.

During transpilation, explicit type nodes are projected separately from capability and
function/operator semantics. The result now reports three fidelity components:

```text
capability_fidelity
expression_semantic_fidelity
type_fidelity
```

The overall ceiling is the worst of those components.

V1 type-projection coverage is deliberately `EXPLICIT_TYPES_ONLY`. Runtime column types are not
invented when schema binding has not supplied them.

Known representation rules such as Snowflake-style `VARIANT` to a JSON-capable target remain
`LOSSY` because data representation can survive while source typing/coercion semantics may not.
Likewise, a STRUCT-to-JSON fallback is not treated as exact merely because the payload can be
serialized.

The dedicated type graph is dependency evidence. It does not establish engine acceptance or
cross-engine behavioral equivalence.


## Differential conformance evidence

SQL Connectome now implements the first bounded differential-execution evidence layer anticipated by
the mature runtime path.

The V1 harness runs fixed literal/read-only probes against hardened DuckDB and SQLite plus PostgreSQL
when a configured runtime is available. It normalizes observed rows and compares value projections
separately from runtime type-family projections.

This evidence is intentionally fixture-scoped:

- `AGREE` means the participating engines agreed on one exact probe under exact runtime versions;
- `DIVERGE` means at least two successful engines produced different normalized observations;
- engine errors remain evidence rather than being coerced into a value result.

Neither agreement nor successful execution changes the project-wide claim ceiling:

`behavioral_equivalence = NOT_ESTABLISHED`

The default probe corpus is source-controlled and snapshot-qualified. Custom internal probe sets are
allowed but carry a weaker provenance label. No arbitrary differential-execution API or MCP tool is
introduced by V1.
