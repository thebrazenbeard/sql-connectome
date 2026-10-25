> **License status:** No repository-wide license file is currently present in this source tree. Do not infer reuse, redistribution, hosting, or commercial permission from repository visibility alone; separately identified third-party components remain governed by their own licenses.

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

For Supabase-class platform parity and qualified BT2/Vera cutover gates, see
[`docs/SUPABASE_REPLACEMENT_GATES.md`](docs/SUPABASE_REPLACEMENT_GATES.md).

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
- a governed expression-semantic registry with stable function/operator IDs and explicit unknowns;
- canonical type families plus dialect coercion graphs with explicit type-projection fidelity;
- explicit parsed type identities embedded directly in semantic IR nodes with source type-graph provenance;
- bounded differential conformance probes across DuckDB, SQLite, and PostgreSQL with fixture-scoped agreement/divergence evidence;
- query-scoped expression contracts exposing argument shape, type rules, and dialect coercions.

Parsing and transpilation do **not** establish cross-engine behavioral equivalence. The API reports
behavioral equivalence as `NOT_ESTABLISHED` until stronger schema/type/engine validation exists.

The optional provider-neutral DB-API/ADBC `ConnectionIdentity` receipt is **HOST_ASSERTED**:
its provider, endpoint, catalog, and session fields are constructor inputs, not independent
server attestation. Its digest cannot prove which physical database was reached; deployment
or currentness decisions require a separately verified endpoint/provider identity.
The adapter refuses a declared `postgresql` engine over a native SQLite connection (and the
reverse), both at session creation and immediately before SQL execution. This checks a
recognized driver family, **not** the reported engine version, remote endpoint, database
identity, or provider ownership. An execution also pins the checked connection/identity
pair for the returned receipt across injected authorization callbacks. Unknown drivers
remain unqualified for execution.

### PostgreSQL execution/governance substrate

The first execution substrate remains the provider-neutral PostgreSQL control plane:

- FastAPI control service with bearer authentication;
- runtime identity and canonical receipts;
- bounded read-only SQL execution inside PostgreSQL read-only transactions,
  now gated off by default for caller-supplied REST/MCP SQL (set
  `SQL_CONNECTOME_ENABLE_ADHOC_POSTGRESQL=true` only for a separately qualified
  private operator role; this does not establish end-user tenant/RLS isolation);
- schema inventory;
- Lantern current-cut adapter using one `REPEATABLE READ READ ONLY` transaction,
  with BT2 V4 PostgreSQL `jsonb::text` SHA-256 payload-digest rechecks before
  emitting a cut receipt (this does not independently authenticate the database);
- checksum-bound migration ledger;
- local PostgreSQL Docker development;
- integration CI against PostgreSQL 17;
- provider-independent custom-format backup + blank-target restore qualification with
  checksum-bound manifests and readback.

Operator query limits are validated at startup and on settings assignment:
`SQL_CONNECTOME_STATEMENT_TIMEOUT_MS` is 1–60,000 (default 5,000) and
`SQL_CONNECTOME_MAX_ROWS` is 1–10,000 (default 500). Invalid values fail closed;
PostgreSQL's `statement_timeout=0` unlimited mode is not accepted.

PostgreSQL is the first execution/governance adapter, not the definition or semantic ceiling of SQL
Connectome.

Recovery is intentionally provider-independent, but backup/restore are explicit
operator actions, not a managed backup service. Without `--overwrite`, backup
publication refuses to replace an archive or manifest claimed by another process;
the two filenames are **not** published as one atomic pair. Backup-path link and
Windows junction checks are preflight safeguards, not protection from a hostile
writer racing parent-directory changes. Use an operator-controlled destination.
Restore requires a trusted source and a separately quiesced blank target; a
checksum-valid archive does not authenticate its producer. See `docs/RECOVERY.md`.

Differential engine evidence is fixture-bounded and does not establish universal behavioral equivalence. See `docs/DIFFERENTIAL_CONFORMANCE.md`.

### MCP / ChatGPT surface

The source-controlled MCP v2 server exposes the semantic plane and governed PostgreSQL read
substrate over Streamable HTTP. Its current tool surface includes dialect inventory/comparison,
dialect probing/parsing, expression semantic/contract inspection, translation planning/transpilation,
type/coercion graph inspection, PostgreSQL validation/qualification, schema/runtime inspection,
bounded read-only queries, migration-state inspection, and Lantern current-cut reads.

No protected write tool is exposed. Caller-supplied live PostgreSQL execution and
planning are disabled by default even when their read-oriented tools are listed.
Network deployment fails closed unless MCP resource-server authentication is
configured. The included static-token verifier is for private development, not
production OAuth identity or tenant/RLS isolation. The source-controlled server
and container entrypoints do not establish that a live endpoint is deployed,
selected, or qualified for a particular BT2/Vera consumer. See
`docs/MCP_CHATGPT.md` and `docs/HOSTING.md`.

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
SQL Connectome does not itself host PostgreSQL or yet implement a complete
Supabase-class Auth, Realtime, Storage, Functions, and dashboard stack; the
current scope and cutover gates are in `docs/SUPABASE_REPLACEMENT_GATES.md`.

An operator-only, read-only PostgreSQL target admission check is available at
`scripts/admit_postgres_target.py`. It cross-checks a registered PRIMARY against
TLS/role/database, migration/facade, and independently pinned cluster identity,
while returning redacted `PASS | FAIL | UNKNOWN` evidence. **PASS does not deploy,
provision, attest provider ownership, or authorize a cutover.** See
`docs/POSTGRES_TARGET_ADMISSION.md`.

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

The CI source guard runs on Ubuntu and Windows **before** dependency installation,
migrations, or container builds. Every workflow that executes checked-out source
also runs it immediately after checkout. It rejects editor folder-open task
execution, repository-provided automatic-task consent, editor symlinks, and
unreviewed or changed font assets using exact source-bound SHA-256 pins (plus
WOFF/WOFF2 signature checks). To repeat its inert checks:

```bash
python scripts/check_editor_startup_source.py
python -m unittest discover -s tests -p test_editor_startup_guard.py -v
```

This verifies the checked-out source only. A reviewed font update must also
update the pin list. Neither a guard pass nor a hash match establishes whether
a previous editor session ran a task or whether a workstation is uncompromised.

## Authority boundary

Source code, an installed adapter, a valid translation plan, successful validation, or a successful
database read does not grant write authority.

Provider provisioning, credential changes, durable migrations, restore, destructive operations,
plugin installation, and protected writes remain separate effects requiring explicit authority and
post-effect verification.
