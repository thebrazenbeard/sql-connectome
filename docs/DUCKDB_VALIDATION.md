# DuckDB Target-Engine Validation

## Purpose

DuckDB is SQL Connectome's first embedded non-PostgreSQL target-engine validator. It provides
engine-backed parser/binder/planner evidence without requiring a remote service or credentials.

A PASS means:

- SQL Connectome admitted the statement as one read-only SELECT;
- the exact embedded DuckDB runtime accepted the supplied catalog shape;
- plain `EXPLAIN` produced a plan;
- the SELECT itself was not executed.

A PASS does **not** establish behavioral equivalence with another SQL engine.

## Runtime boundary

Each validation call receives a fresh `:memory:` DuckDB connection. Before caller SQL is planned,
SQL Connectome:

1. disables external access;
2. disallows unsigned and community extensions;
3. disables known-extension auto-install and auto-load;
4. limits execution resources to one thread and 256 MB of memory;
5. materializes only the caller-supplied table/column/type schema;
6. locks DuckDB configuration;
7. runs plain `EXPLAIN`, never `EXPLAIN ANALYZE`.

The receipt binds the SQL digest, schema-context digest, validation result, and exact runtime
identity/configuration digest.

## External-access boundary

DuckDB can ordinarily read files and external sources through functions such as `read_csv`,
`read_parquet`, and `read_json`. SQL Connectome disables external access before caller SQL is
planned. The regression suite explicitly verifies that planning a local-file reader fails under
that configuration.

## Authority boundary

The embedded validator is not a general DuckDB execution surface. It exposes no arbitrary DDL/DML,
no durable database file, no extension installation, and no query-result execution path.

`VALIDATE != EXECUTE != AUTHORIZE`

Upstream references:

- https://duckdb.org/docs/current/guides/meta/explain
- https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview
- https://duckdb.org/docs/current/operations_manual/securing_duckdb/securing_extensions
