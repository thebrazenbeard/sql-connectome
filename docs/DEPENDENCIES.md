# Dependency Boundaries

## SQLGlot

SQL Connectome uses SQLGlot as a parser/transpiler peripheral.

Current source pin:

`sqlglot>=30.19,<30.20`

Reasons for the narrow compatibility line:

- SQLGlot documents minor versions as potentially backwards-incompatible;
- SQL Connectome binds parser behavior to tests rather than silently accepting dependency drift;
- dialect parsing/transpilation remains replaceable behind the connectome semantic model.

SQLGlot is MIT licensed.

SQLGlot does **not** define SQL Connectome's truth model. In particular:

- parser acceptance is not target-engine validation;
- generated SQL is not proof of behavioral equivalence;
- SQLGlot warnings/errors do not grant execution authority;
- SQL Connectome capability, provenance, fidelity, validation, and governance state remain separate.

If SQLGlot is replaced or supplemented, the replacement must preserve these boundaries and pass the
same connectome contracts.


### Parser resource bounds

SQLGlot's parser defaults to an unlimited AST-node count. SQL Connectome overrides that default with
a 10,000-node ceiling, caps the dialect token stream at 20,000 tokens, and independently caps
accepted SQL text at 50,000 characters. These are
defense-in-depth limits against pathological parser/memory workloads; they are not semantic limits
of SQL itself.

Dialect probing applies the same text/token/AST ceilings to every candidate parser. SQL Connectome
sets the inherited parser node ceiling after dialect-specific parser construction because not every
SQLGlot dialect constructor accepts the generic `max_nodes` keyword even though the base parser
supports the guard. Adding a new dialect adapter
does not require changing a duplicated API maximum: the runtime registry remains the dialect-count
source of truth.


### Dialect semantic flags

The expression-conformance layer currently treats the pinned SQLGlot dialect flags as dependency
evidence, not as SQL Connectome authority. The relevant upstream flags include NULL ordering,
typed/safe division, CONCAT NULL handling, LEAST/GREATEST NULL handling, index offsets, string
concat strictness, user-defined-type support, and two-argument LOG ordering.

Upstream references:

- https://sqlglot.com/sqlglot/dialects.html
- https://github.com/tobymao/sqlglot/blob/main/sqlglot/dialects/dialect.py

These flags are version-bound by the SQLGlot dependency pin. A future SQLGlot upgrade must rerun the
semantic divergence suite before the dependency range is moved.


### Expression metadata and coercions

SQL Connectome's expression-contract API reads the pinned SQLGlot dialect
`EXPRESSION_METADATA` and `COERCES_TO` structures. It intentionally serializes only stable,
descriptive evidence such as fixed return types, presence of an annotator, argument shape, and
coercion edges. Internal Python callables are never exposed as durable contract data.

Upstream reference:

- https://sqlglot.com/sqlglot/typing.html


## Model Context Protocol Python SDK

SQL Connectome uses the official Model Context Protocol Python SDK for its ChatGPT/MCP interface.

Current source range:

`mcp>=2,<3`

The V2 line is used because it implements the current 2026 MCP transport model while retaining
compatibility with earlier MCP protocol revisions. SQL Connectome uses the high-level
`MCPServer` API and Streamable HTTP transport.

The SDK is a transport/interface dependency. It does **not** define SQL Connectome semantics,
translation fidelity, database authority, or provenance.

Dependency admission rules:

- MCP tools call the same internal semantic/control functions used by the REST surface;
- MCP transport success does not upgrade semantic or behavioral-equivalence claims;
- an MCP connection or plugin installation does not grant database-write authority;
- network serving fails closed unless resource-server authentication is configured;
- MCP upgrades must preserve the exact tool inventory and in-process client qualification tests.

Upstream reference:

- https://github.com/modelcontextprotocol/python-sdk


## DuckDB

SQL Connectome uses the embedded DuckDB Python package as its first non-PostgreSQL target-engine
validator.

Current source range:

`duckdb>=1.5.5,<1.6`

The validator creates a fresh in-memory database for each call, installs only caller-supplied schema
shapes, locks configuration, and runs plain `EXPLAIN` rather than `EXPLAIN ANALYZE`. DuckDB's
documentation states that plain `EXPLAIN` produces the query plan without executing the query.

The embedded validator disables external access, community extensions, unsigned extensions,
automatic known-extension installation, and automatic known-extension loading. It also constrains
the runtime to one thread and a 256 MB memory limit before configuration is locked.

Dependency evidence does not establish cross-engine behavioral equivalence. A PASS means the exact
DuckDB runtime accepted and planned the SQL against the supplied in-memory catalog.

Upstream references:

- https://duckdb.org/docs/current/guides/meta/explain
- https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview
- https://duckdb.org/docs/current/operations_manual/securing_duckdb/securing_extensions


## SQLite (Python standard library)

SQL Connectome uses Python's standard-library `sqlite3` module as its embedded SQLite target-engine
validator. No additional SQLite package is admitted by this slice.

Each validation call creates a fresh in-memory connection, materializes only the caller-supplied
schema, enables `PRAGMA query_only=ON`, disables extension loading, disables trusted-schema
behavior, installs a compile-time authorizer that allows SELECT/READ/function/recursive-select
actions only, applies resource limits, and invokes `EXPLAIN QUERY PLAN`.

SQLite documents `query_only` as rejecting CREATE, DELETE, DROP, INSERT, and UPDATE; its
authorizer runs during statement compilation; and `EXPLAIN QUERY PLAN` reports the strategy that
would have been used by the underlying statement. SQL Connectome does not treat the plan output
format as a stable semantic API.

A PASS means the exact bundled SQLite runtime accepted and planned the SQL against the supplied
in-memory catalog. It does not establish cross-engine behavioral equivalence and does not execute
the underlying SELECT.

Upstream references:

- https://www.sqlite.org/pragma.html#pragma_query_only
- https://www.sqlite.org/c3ref/set_authorizer.html
- https://www.sqlite.org/eqp.html
- https://www.sqlite.org/lang_explain.html
