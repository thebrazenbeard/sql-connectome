# SQLite Target-Engine Validation

## Purpose

SQLite is SQL Connectome's second embedded target-engine validator and requires no dependency beyond
Python's standard-library `sqlite3` module.

A PASS means:

- SQL Connectome admitted the statement as one read-only SELECT;
- the exact bundled SQLite runtime accepted the supplied catalog shape;
- `EXPLAIN QUERY PLAN` produced a plan;
- the underlying SELECT was not executed.

A PASS does **not** establish behavioral equivalence with another SQL engine.

## Runtime boundary

Each validation call receives a fresh `:memory:` SQLite connection. Before caller SQL is planned,
SQL Connectome:

1. applies explicit SQLite resource limits;
2. materializes only the caller-supplied table/column/type schema;
3. disables extension loading;
4. sets `trusted_schema=OFF`;
5. sets `query_only=ON`;
6. installs a compile-time authorizer allowing SELECT, READ, function use, and recursive SELECT only;
7. runs `EXPLAIN QUERY PLAN` on the admitted statement.

The receipt binds the SQL digest, schema-context digest, validation result, and exact runtime identity.

## Authorization boundary

The authorizer is installed after SQL Connectome creates the ephemeral validation schema. Caller SQL
therefore cannot compile ATTACH, PRAGMA, DDL, DML, transaction-control, or other non-SELECT actions
through this validation surface.

The connection is ephemeral and exposes no durable SQLite database file.

## Static-analysis review

CodeQL's `py/sql-injection` rule correctly treats Python `sqlite3.execute` as a SQL sink. This
validator necessarily has two dynamic SQL sinks: construction of the caller-described ephemeral
schema and planning of the caller SQL itself.

Both sinks are explicitly reviewed and backed by executable controls: SQLite identifier quoting,
SQLGlot type parse/regeneration, delimiter rejection, single-statement/top-level-SELECT admission,
`query_only`, compile-time authorization, explicit `load_extension` denial, a fresh in-memory
database, and regression tests for statement and schema smuggling.

CodeQL cannot infer those application-specific sanitizers, so the two exact PR-introduced findings
are triaged as reviewed false positives in GitHub with an audit explanation. The
`py/sql-injection` query remains enabled and no source-wide suppression or query exclusion is
used. Any new dynamic SQL sink remains independently subject to CodeQL.

## Plan-output boundary

SQLite explicitly warns that EXPLAIN QUERY PLAN output is intended for interactive analysis and may
change between releases. SQL Connectome records the raw rows as evidence but does not make their
format part of the cross-version semantic contract.

## Authority boundary

`VALIDATE != EXECUTE != AUTHORIZE`

The SQLite validator is not an arbitrary execution surface and does not grant write authority.

Upstream references:

- https://www.sqlite.org/pragma.html#pragma_query_only
- https://www.sqlite.org/c3ref/set_authorizer.html
- https://www.sqlite.org/eqp.html
- https://www.sqlite.org/lang_explain.html
