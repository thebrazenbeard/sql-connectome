# SQL Connectome Architecture

## Boundary

SQL Connectome is a multi-dialect semantic connectome with pluggable execution and governance
substrates.

The existing PostgreSQL V1 is deliberately retained as the first execution/control substrate. It
is not a PostgreSQL fork and PostgreSQL is not the semantic boundary of the project.

The backing database provider is replaceable. Provider APIs provision infrastructure; they do not
define SQL Connectome semantics, migration history, currentness, translation fidelity, or tool
behavior.

## Semantic plane

The semantic plane owns:

1. **Dialect genomes** — version-aware dialect identities and capability bundles.
2. **Semantic IR** — graph-shaped representation that may retain dialect-specific semantics.
3. **Capability graph** — explicit feature support rather than family-name inference.
4. **Rewrite knowledge** — target-dependent transformations with declared fidelity.
5. **Translation loss** — preserved evidence when target semantics cannot remain exact.
6. **Parser/generator adapters** — future components that map text into/out of semantic IR.
7. **Validation adapters** — static binding plus target-engine qualification paths. PostgreSQL V1 can now perform read-only, non-ANALYZE `EXPLAIN` validation.

The semantic plane follows:

`UNDERSTAND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`

See `CONNECTOME_MODEL.md`.

## Execution/governance plane

The first executable substrate contains:

1. **PostgreSQL substrate** — ordinary PostgreSQL 16/17.
2. **Canonical migrations** — source-controlled, checksum-bound, replayable.
3. **Control API** — authenticated FastAPI service.
4. **Read boundary** — single SELECT plus PostgreSQL READ ONLY transaction, timeout and row cap.
5. **Currentness adapter** — Lantern cut/payload captured in one REPEATABLE READ READ ONLY snapshot.
6. **Receipts** — canonical digests bind responses to runtime identity and exact subjects.
7. **ChatGPT/MCP adapter** — current MCP v2/Streamable HTTP layer exposing semantic and governed
   read tools without adding write authority.

The execution layer is intentionally separable from semantic reasoning. Understanding Oracle SQL,
for example, does not require an Oracle execution credential, and having a PostgreSQL connection
does not make PostgreSQL the meaning of a foreign dialect.

## Bootstrap API

The semantic slice exposes:

- `GET /v1/connectome/dialects`
- `POST /v1/connectome/translation-plan`

These surfaces report admitted capability knowledge only. They do not generate target SQL.

The MCP surface composes the same internal functions rather than proxying the REST API. That keeps
semantic, execution, receipt, and authority behavior identical across interfaces while avoiding an
extra HTTP hop. See `MCP_CHATGPT.md`.

## Optional components

PostgREST and postgres-meta are composable candidates, not mandatory runtime dependencies.
Realtime, Auth, storage, GraphQL, cloud-scale pooling, foreign-engine adapters, and parser engines
are admitted only when a consumer demonstrates the need.

## Provider rule

No semantic-plane source path should require Aiven, Supabase, WoWSQL, Neon, or another vendor. A
provider outage must be an infrastructure failure, not a change in SQL Connectome semantics.

## Write rule

The first control API intentionally exposes no protected write API. Migration tooling is an
operator-side command and is not reachable through the HTTP service.

A later write surface must add:

- distinct write identity;
- capability-specific authorization;
- exact currentness preflight;
- idempotency;
- effect receipt persistence;
- post-effect readback.
