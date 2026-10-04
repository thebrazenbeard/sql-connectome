# SQL dialect universe research V2

Reviewed: 2026-10-04

This note records the evidence basis for expanding SQL Connectome's explicit
dialect universe beyond the pinned SQLGlot 30.19 parser surface.

The admission rule is conservative: existence as a documented SQL language or
product dialect is enough to create a catalog node, but it is not enough to
claim parsing, semantic modeling, translation fidelity, or behavioral
equivalence.

## Newly explicit SQL surfaces

- Apache Flink SQL — official Flink documentation describes SQL for streaming
  and batch processing, based on Apache Calcite.
- ksqlDB SQL — Confluent documents a SQL language extended for streaming
  queries, streams, tables, windows, pull queries, and push queries.
- Google Cloud Spanner GoogleSQL — Google documents GoogleSQL as one of
  Spanner's two selectable SQL dialects.
- Google Cloud Spanner PostgreSQL interface — Google documents this as a
  PostgreSQL language subset with Spanner-specific extensions and limitations.
- IBM Informix SQL — IBM explicitly documents the Informix dialect of SQL.
- IBM Netezza Performance Server SQL — IBM documents a distinct Netezza SQL
  implementation with SQL-92 foundations and later extensions.
- H2 SQL — H2 publishes its own SQL grammar and compatibility modes.
- Apache Pinot SQL — Pinot documents a Calcite-backed SQL surface whose
  semantics vary between its single-stage and multi-stage engines.
- CrateDB SQL — CrateDB publishes a complete SQL syntax reference and extends
  SQL for distributed, search, time-series, and administrative behavior.
- QuestDB SQL — QuestDB documents SQL extended with time-series operations such
  as SAMPLE BY, LATEST ON, ASOF JOIN, WINDOW JOIN, and HORIZON JOIN.

## SQL-like language kept outside the SQL dialect graph

Salesforce SOQL is intentionally not admitted as an SQL dialect. Salesforce
describes SOQL as similar to SQL SELECT but with a different object/relationship
model and without arbitrary SQL joins. It remains an explicit SQL-like
non-SQL language classification.

## Compatibility-parser policy

Spanner GoogleSQL currently uses SQLGlot's BigQuery dialect only as a
GoogleSQL-family compatibility parser. Spanner PostgreSQL currently uses
SQLGlot's PostgreSQL dialect only as a compatibility parser. Both retain
semantic, translation, and behavioral coverage as NOT_ESTABLISHED.

All other V2 additions intentionally have parser=NOT_AVAILABLE. Their presence
in the universe means SQL Connectome knows the language exists; it does not
manufacture implementation claims.

## Research sources

Primary evidence was current official documentation from Google Cloud Spanner,
Apache Flink, Confluent ksqlDB, IBM Informix/Netezza, H2, Apache Pinot, CrateDB,
QuestDB, and Salesforce. SQLFluff 4.3.0's documented dialect set was used as a
cross-parser census, not as proof of vendor semantics.


## Compatibility-parser follow-up

A later source review found official compatibility claims strong enough to
justify parser-family bridges for five additional catalog nodes:

- CockroachDB -> PostgreSQL parser compatibility.
- TiDB -> MySQL parser compatibility.
- YugabyteDB YSQL -> PostgreSQL parser compatibility.
- CrateDB -> PostgreSQL parser compatibility.
- QuestDB -> PostgreSQL parser compatibility.

These bridges advance only the parser axis to COMPATIBILITY_ADAPTER. They do
not admit relational semantics, translation fidelity, or behavioral
equivalence. Successful parsing therefore records any observed but unadmitted
capabilities, while binding and translation continue to fail closed until
separate semantic evidence is admitted.
