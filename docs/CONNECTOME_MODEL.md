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

The current code implements the first executable portions of `D`, `I`, `C`, and `R`.
The pre-existing PostgreSQL control plane is retained as the first `E/G/V` substrate rather
than defining the scope of the whole project.

## Dialect genomes

A dialect genome is a version-aware capability bundle, not merely a name.

The bootstrap registry is deliberately conservative. A listed dialect does not imply complete
grammar or conformance coverage. Capabilities are admitted as explicit facts needed by tested
translation rules and will grow under evidence.

Current bootstrap dialects:

- PostgreSQL
- DuckDB
- SQLite
- MySQL
- BigQuery GoogleSQL
- Snowflake SQL
- Microsoft T-SQL
- Oracle SQL
- Trino SQL

A future dialect is added by registering a genome and its semantic connections rather than
modifying one monolithic universal grammar.

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

The current IR envelope validates graph integrity but does not yet parse SQL text into that graph.
Parser admission is a later layer.

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
