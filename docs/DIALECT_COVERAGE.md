# Dialect coverage

SQL Connectome treats dialect recognition, semantic modeling, translation, validation, execution, and authorization as separate claims.

The practical identity of a SQL surface is not just a dialect name. Evidence may need to be scoped to the dialect, engine/product version, relevant configuration or session modes, and the SQL feature family being exercised.

## Coverage axes

Each dialect genome exposes four independent coverage axes:

- `parser`: whether SQL Connectome has a native parser dialect, a compatibility adapter, or no parser.
- `semantics`: whether no semantic claims are established, only a relational baseline is modeled, or dialect-specific capabilities are modeled.
- `translation`: whether capability-level translation planning is available.
- `behavior`: whether semantics have no empirical qualification, embedded-engine differential evidence, or real-engine differential evidence.

These axes are deliberately non-monotonic as a single score. Parser availability is not semantic proof, and behavioral evidence for a finite corpus is not general semantic equivalence.

## Current qualification anchors

PostgreSQL, MySQL, MariaDB, and Trino have real-engine differential evidence. DuckDB and SQLite provide embedded-engine differential evidence.

MariaDB is intentionally represented as its own dialect node while currently using SQLGlot's MySQL parser as a compatibility adapter. That adapter does not imply that MariaDB-specific syntax or semantics are identical to MySQL.

The source-controlled differential corpus remains bounded. Its evidence can establish behavior for the exercised probes and exact engine/runtime context only. `behavioral_equivalence` and broad `generalization` remain `NOT_ESTABLISHED`.

## Parser-backed baseline dialects

SQLGlot parser support is broader than SQL Connectome's admitted dialect-specific semantics. Parser-backed baseline dialects therefore begin at `RELATIONAL_BASELINE` unless stronger evidence is explicitly represented.

SQLGlot itself documents that parsing is intentionally lenient and is not SQL validation. SQL Connectome therefore never treats successful parsing or transpilation as engine validation.

## Known SQL dialects without a parser

The catalog also carries explicit nodes for important SQL dialects whose parser support is not yet established here: CockroachDB SQL, IBM Db2 SQL, Firebird SQL, Apache Impala SQL, SAP HANA SQL, TiDB SQL, Vertica SQL, and YugabyteDB YSQL.

These nodes intentionally have `parser=NOT_AVAILABLE` and `semantics=NOT_ESTABLISHED`. They are visible so absence of implementation cannot be confused with absence from the SQL universe. Parser-dependent operations fail closed for them.

## SQLGlot surfaces that are not SQL dialect nodes

The pinned SQLGlot dependency also exposes DAX, PRQL, and Tableau parser/generator surfaces. SQL Connectome does not classify these as ordinary SQL dialect genomes:

- DAX is a formula/expression language.
- PRQL is handled through the receptor boundary rather than represented as SQL.
- Tableau custom SQL ultimately uses the underlying database SQL dialect, while Tableau's own query-generation layer is not itself a database SQL dialect.

This classification prevents dependency surface area from silently expanding SQL semantic claims.

## Evidence rule

A dialect capability should advance only when evidence justifies the stronger state. The intended progression is not "parser exists, therefore supported"; it is explicit evidence for the exact claim being made.

The standing invariant remains:

`UNDERSTAND != BIND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`


## SQL feature families

Dialect maturity and SQL feature coverage answer different questions. Dialect maturity says how strongly the dialect itself is qualified. Feature-family coverage says which portions of the SQL language SQL Connectome currently models for that dialect.

The V1 feature-family universe includes relational query semantics, data definition, data modification, type systems, constraints, transactions/locking, procedural routines, session control, security/authorization, metadata/schemata, external-data federation, JSON/document semantics, XML, nested collections, analytics, geospatial, property graphs, multidimensional data, vectors, streaming/incremental semantics, and administration.

Current capabilities are assigned to exactly one primary feature family. The default catalog test fails if an admitted capability has no family assignment.

SQL:2023 module alignment is kept separately from dialect capabilities. In particular, SQL/PSM anchors procedural routines, SQL/MED external-data federation, SQL/Schemata metadata/schema surfaces, SQL/XML XML semantics, SQL/MDA multidimensional arrays, and SQL/PGQ property-graph queries. Framework, CLI, OLB, and Java binding parts remain visible without being falsely represented as ordinary SQL statement families.

A feature-family state of `NOT_MODELED` means precisely that: the catalog does not currently claim semantic coverage for that family. It does not mean the underlying database product lacks the feature.
