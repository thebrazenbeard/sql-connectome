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
