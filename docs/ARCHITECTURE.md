# SQL Connectome V1 Architecture

## Boundary

SQL Connectome is a control plane around standard PostgreSQL, not a fork of PostgreSQL.

The backing provider is replaceable. Provider APIs provision infrastructure; they do not define database semantics, Lantern currentness, migration history, or ChatGPT tool behavior.

## Components

1. **PostgreSQL substrate** — ordinary PostgreSQL 16/17.
2. **Canonical migrations** — source-controlled, checksum-bound, replayable.
3. **Control API** — authenticated FastAPI service.
4. **Read boundary** — single SELECT plus PostgreSQL READ ONLY transaction, timeout and row cap.
5. **Currentness adapter** — Lantern cut/payload captured in one REPEATABLE READ READ ONLY snapshot.
6. **Receipts** — canonical digests bind responses to runtime identity and exact subjects.
7. **ChatGPT/MCP adapter** — next layer; it calls this control plane rather than a provider API.

## Optional components

PostgREST and postgres-meta are composable candidates, not mandatory runtime dependencies. Realtime, Auth, storage, GraphQL and cloud-scale pooling are deferred until a consumer demonstrates the need.

## Provider rule

No source path above the provider adapter may require Aiven, Supabase, WoWSQL, Neon, or another vendor. A provider outage must be an infrastructure failure, not a change in SQL Connectome semantics.

## Write rule

V1 intentionally exposes no protected write API. Migration tooling is an operator-side command and is not reachable through the HTTP service.

A later write surface must add:
- a distinct write identity;
- capability-specific authorization;
- exact currentness preflight;
- idempotency;
- effect receipt persistence;
- post-effect readback.
