# Differential Conformance V1

## Purpose

SQL Connectome can now collect bounded empirical evidence from multiple SQL engines without
collapsing that evidence into a universal behavioral-equivalence claim.

The V1 harness executes a small fixed corpus against:

- hardened in-memory DuckDB;
- hardened in-memory SQLite;
- PostgreSQL through the existing READ ONLY transaction path when a configured runtime is present.

The default corpus is source-controlled and is run by the Conformance Snapshot workflow against
PostgreSQL 17 plus the pinned embedded-engine versions.

## Evidence model

Every probe records:

- the exact SQL and probe purpose;
- per-engine PASS, ERROR, or NOT_RUN state;
- exact runtime identity when available;
- normalized rows;
- a value projection;
- a type-family projection;
- an execution outcome;
- a value agreement/divergence outcome;
- a type agreement/divergence outcome.

Value and type comparisons are intentionally separate. For example, two engines may return the same
numeric value using different runtime type families.

Possible comparison outcomes include:

- `AGREE`;
- `DIVERGE`;
- `INSUFFICIENT_SUCCESSFUL_ENGINES`.

Execution state is reported separately as `ALL_PASS`, `MIXED_PASS_ERROR`, or `ALL_ERROR`.

## Claim ceiling

The evidence scope is fixture-bounded.

`AGREE` means the participating engines produced the same normalized observation for that exact
probe under those exact runtime versions. It does not establish equivalence for other inputs,
schemas, sessions, versions, or surrounding queries.

`DIVERGE` is stronger negative evidence: the observed engines did not agree for that exact probe.

Every result therefore retains:

`behavioral_equivalence = NOT_ESTABLISHED`

and the overall artifact retains:

`generalization = NOT_ESTABLISHED`

## Corpus provenance

The built-in corpus is labeled `DEFAULT_SOURCE_CONTROLLED` and receives the evidence scope
`FIXED_SOURCE_CONTROLLED_PROBES_ONLY`.

The library function can also accept a bounded custom probe tuple for internal tests or experiments.
Those results are labeled `BOUNDED_LIBRARY_INPUT` with the weaker scope
`BOUNDED_PROBE_SET_ONLY`.

Probe IDs must be unique and the corpus is capped at 64 probes. Each query must pass the existing
single-SELECT read guard and result rows are capped at 32 by the differential harness.

## Runtime safety

DuckDB probes reuse the same hardened session as DuckDB validation:

- fresh `:memory:` database;
- external access disabled;
- unsigned/community extensions disabled;
- extension auto-install/auto-load disabled;
- one thread;
- 256 MB memory limit;
- locked configuration.

SQLite probes reuse the same hardened session as SQLite validation:

- fresh `:memory:` database;
- extension loading disabled;
- `trusted_schema=OFF`;
- `query_only=ON`;
- compile-time SELECT/READ/function authorizer;
- explicit `load_extension` denial;
- SQLite resource limits.

PostgreSQL probes use the existing bounded read-only execution path with a PostgreSQL READ ONLY
transaction, statement timeout, and row cap.

V1 exposes no REST or MCP differential-execution tool. The harness is repository qualification
infrastructure, not a new arbitrary execution surface.

## Durable artifact

`.github/workflows/conformance.yml` emits:

- `artifacts/conformance-snapshot.json`;
- `artifacts/differential-conformance.json`.

The differential receipt binds the corpus digest, observed result digest, source commit,
PostgreSQL-inclusion state, probe count, and corpus origin.
