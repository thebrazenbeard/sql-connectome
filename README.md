# SQL Connectome

SQL Connectome is a semantic network for understanding, comparing, translating, validating,
routing, and safely executing SQL-family languages without pretending that every dialect has the
same grammar or semantics.

The project is built around three separations:

- dialect syntax is not semantic identity;
- translation is not proof of behavioral equivalence;
- understanding or routing a query is not authority to execute its effects.

## Architecture

The connectome models dialects as version-aware **dialect genomes** attached to a shared,
graph-shaped semantic intermediate representation. Capabilities and rewrite rules connect those
genomes while preserving whether a translation is:

- `EXACT`;
- `CONSTRUCTIVE`;
- `LOSSY`;
- `UNREPRESENTABLE`.

The semantic core is intentionally open-ended. New SQL engines and dialects attach by contributing
a genome, capabilities, semantic bindings, and rewrite/validation knowledge rather than forcing
every language into one monolithic grammar.

See `docs/CONNECTOME_MODEL.md` for the semantic model.

### Governed dialect catalog

The executable semantic core now binds dialect genomes, parser adapters, and rewrite rules through an
immutable `ConnectomeCatalog`. `DEFAULT_CATALOG` is the source-controlled runtime admission state.

Library callers can derive an extended catalog with `admit_dialect(...)`; admission is copy-on-write
and validates canonical IDs, alias ownership, and parser-adapter bindings. Parsing, static binding,
contract/type inspection, dialect probing, and transpilation can consume that explicit catalog.

The network REST/MCP surfaces intentionally continue to use the source-controlled default catalog.
SQL Connectome does **not** auto-discover or auto-admit installed dialect plugins: installation is not
semantic authority, validation evidence, execution authority, or permission to change the live
runtime. Conformance snapshots bind the default catalog with a canonical digest.


## Current executable slices

### Semantic connectome

The current semantic-core slice includes:

- versionable dialect-genome structures;
- semantic dimensions spanning relational, nested, document, graph, vector, geospatial, temporal,
  streaming, analytical, transactional, procedural, administrative, and federated SQL;
- a graph-shaped universal SQL semantic IR envelope;
- a deterministic capability/rewrite planner;
- explicit translation-fidelity and semantic-loss states;
- bootstrap genomes for PostgreSQL, DuckDB, SQLite, MySQL, BigQuery GoogleSQL, Snowflake,
  Microsoft T-SQL, Oracle SQL, and Trino;
- authenticated dialect inventory and translation-plan APIs;
- dialect-aware SQL text parsing through a pinned SQLGlot adapter;
- SQLGlot AST projection into the graph-shaped semantic IR;
- strict transpilation gated by the connectome capability plan;
- target-dialect reparse validation;
- lossy-translation opt-in and unrepresentable-translation blocking;
- 28 SQL-family parser adapters/genomes with deliberately partial capability admission where needed;
- heuristic dialect probing that returns ranked evidence and preserves ambiguity rather than claiming identity;
- first-class dialect comparison across admitted capabilities, semantic dimensions, SQLGlot dialect flags, and type/coercion graph summaries without inventing a compatibility score;
- schema-aware static binding with identifier qualification, star expansion, and type annotation;
- real PostgreSQL target validation through read-only, non-ANALYZE JSON EXPLAIN;
- hardened in-memory DuckDB target validation through non-executing EXPLAIN with external access disabled;
- hardened in-memory SQLite target validation through EXPLAIN QUERY PLAN with query-only mode and a compile-time authorizer;
- end-to-end foreign-dialect → PostgreSQL translation qualification with one provenance receipt;
- expression-level function/operator/type inventories and dialect-semantic risk ceilings;
- canonical type families plus dialect coercion graphs with explicit type-projection fidelity;
- bounded differential conformance probes across DuckDB, SQLite, and PostgreSQL with fixture-scoped agreement/divergence evidence;
- query-scoped expression contracts exposing argument shape, type rules, and dialect coercions.

Parsing and transpilation do **not** establish cross-engine behavioral equivalence. The API reports
behavioral equivalence as `NOT_ESTABLISHED` until stronger schema/type/engine validation exists.

### PostgreSQL execution/governance substrate

The first execution substrate remains the provider-neutral PostgreSQL control plane:

- FastAPI control service with bearer authentication;
- runtime identity and canonical receipts;
- bounded read-only SQL execution inside PostgreSQL read-only transactions;
- schema inventory;
- Lantern current-cut adapter using one `REPEATABLE READ READ ONLY` transaction;
- checksum-bound migration ledger;
- local PostgreSQL Docker development;
- integration CI against PostgreSQL 17;
- provider-independent custom-format backup + blank-target restore qualification with
  checksum-bound manifests and readback.

PostgreSQL is the first execution/governance adapter, not the definition or semantic ceiling of SQL
Connectome.

Recovery is intentionally provider-independent. See `docs/RECOVERY.md`.

Differential engine evidence is fixture-bounded and does not establish universal behavioral equivalence. See `docs/DIFFERENTIAL_CONFORMANCE.md`.

### MCP / ChatGPT surface

The source-controlled MCP v2 server exposes the semantic plane and governed PostgreSQL read
substrate over Streamable HTTP. Its current tool surface includes dialect inventory/comparison,
dialect probing/parsing, translation planning/transpilation, type/coercion graph inspection, PostgreSQL validation/qualification, schema/runtime inspection,
bounded read-only queries, migration-state inspection, and Lantern current-cut reads.

No protected write tool is exposed. Network deployment fails closed unless MCP resource-server
authentication is configured. See `docs/MCP_CHATGPT.md` and `docs/HOSTING.md`.

### Project/database control plane

The first platform-lifecycle slice adds provider-neutral projects and database targets:

- stable logical project identities;
- primary/replica/analytics/archive target roles;
- provider/region/resource metadata with credentials kept outside the control-plane schema;
- one-live-primary enforcement;
- runtime-bound project inventory receipts;
- append-only effect receipts;
- operator-only project/target registration.

Registration is deliberately separate from provider provisioning. See
`docs/PROJECT_CONTROL_PLANE.md`.

## Local development

```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export SQL_CONNECTOME_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/sql_connectome'
export SQL_CONNECTOME_API_TOKEN='local-dev-token'
python scripts/apply_migrations.py
uvicorn sql_connectome.app:app --reload
```

The authenticated MCP server is a separate entrypoint:

```bash
sql-connectome-mcp
```

Run tests:

```bash
pytest
ruff check .
```

## Authority boundary

Source code, an installed adapter, a valid translation plan, successful validation, or a successful
database read does not grant write authority.

Provider provisioning, credential changes, durable migrations, restore, destructive operations,
plugin installation, and protected writes remain separate effects requiring explicit authority and
post-effect verification.
