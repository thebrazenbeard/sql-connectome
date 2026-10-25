# From governed SQL engine to Supabase-class platform

This is a target architecture and qualification backlog, **not a feature-parity or
deployment claim**. SQL Connectome is intended to replace reliance on a specific
database platform for BT2/Vera first, and may later provide equivalent application
services. Its semantic SQL plane remains provider-neutral throughout.

## Upstream architecture as a comparison, not an implementation shortcut

The upstream `supabase/supabase` repository composes PostgreSQL, Auth/GoTrue,
PostgREST and GraphQL, Realtime, object storage, Edge Functions, Studio, gateway,
pooling, and observability. Those independently operated services are not all
implemented by SQL Connectome. No upstream source is copied in this document;
each candidate component requires its own license, source, threat-model, and
upgrade review before admission.

| Capability | Current SQL Connectome source | Admission and proof needed |
| --- | --- | --- |
| SQL semantics and explicit UNKNOWN | Implemented, fixture-bounded | Keep parser/engine conformance and deterministic false-positive probes |
| PostgreSQL substrate | External PostgreSQL URL; no hosting | Provisioned, backed-up cluster with endpoint/TLS/physical identity readback |
| Governed REST/MCP | Static bearer bootstrap; read-oriented surface | Private authenticated deployment and external consumer end-to-end probe |
| Project registry | Metadata and logical target bindings | Separate provider provisioning effects and verified post-effect readback |
| End-user auth and tenant scope | Not implemented | Verified issuer/JWKS, token rotation, identity-to-SQL role/RLS binding |
| Generated application data API | Not equivalent to PostgREST/GraphQL | Schema-aware API, per-request claims, deny-by-default policy tests |
| Realtime | Not implemented | Session reauthentication, topic/RLS isolation, replay/ordering tests |
| Object storage | Not implemented | Object/bucket ACLs, signed URL expiry, audit and retention tests |
| Functions and dashboard | Not implemented | Sandboxed execution, constrained roles, operator authentication |
| Pooling, observability, HA | Not implemented as a complete stack | Tenant isolation, load/failure tests, upgrade and disaster-recovery drills |

## Minimum useful cutover: BT2 Lantern read-only material access

1. Select an explicitly owned durable PostgreSQL target. Record provider resource
   identity, TLS-verified endpoint, and a physical PostgreSQL identity when
   accessible; if not measurable, mark physical identity `UNKNOWN`. The existing
   SQL Connectome `_runtime_identity` digest is **logical metadata**, not a
   physical-cluster attestation. `POSTGRES_TARGET_ADMISSION.md` describes an
   operator-only read-only preflight with independently pinned expected identity;
   its bounded PASS remains below runtime/consumer cutover qualification.
2. Reconstruct source-controlled SQL Connectome and BT2 schemas from a blank
   target; verify migration checksums, role grants, function search path, and
   denied cross-schema access. Credentials remain outside registry metadata.
   The historical WoWSQL V3 Project role reads only `bt2_project_read` and is
   denied direct `bt2` access, whereas the candidate SQL Connectome V4 adapter
   currently calls `bt2.material_cut_v1` and `bt2.runtime_visible_materials_v1`
   directly. Qualify the exact V4 schema and grants on the actual target; a
   disposable V4 PostgreSQL CI pass does **not** install that role contract.
3. Deploy a private, authenticated MCP/REST endpoint. Test the actual remote
   transport and authorization failure cases; in-process MCP tests are narrower.
4. Read `lantern_current_cut(PROJECT_LANTERN)` using a PostgreSQL repeatable-read,
   read-only transaction. Verify cut membership, profile/policy bindings, and
   canonical payload digests. Demand a documented nonempty/currentness condition
   for the specific consumer before treating the result as accepted.
5. Run negative tests for missing views, corrupted payload/digest, revoked DB
   grants, unavailable server, wrong target, stale policy, and unauthorized tool
   caller. On any unqualified result, hold consumer promotion as `UNKNOWN`.
6. Rebuild and restore into a separately quiesced blank target. Check not just
   archive bytes/catalog/migrations, but row-data equivalence, ownership, roles,
   extensions, policies, and post-restore application behavior. Qualify RPO/RTO.
7. Switch one explicit BT2/Vera consumer only after source, build, deployed
   route, authenticated readback, recovery and human-approved effect gates pass.
   Preserve the prior provider until the new route has independent sustained
   behavioral evidence and rollback is qualified.

This cutover is not permission to drop Supabase, WoWSQL, or any legacy cluster.
Provider retirement is a distinct protected effect after data and consumer
reconciliation. There is no silent fallback to a different database.

## What “better” must mean before anyone claims it

For each admitted workload, compare SQL Connectome and the prior service on a
pinned data set and runtime under the same threat model: denied cross-tenant
reads/writes, semantic fidelity/UNKNOWN behavior, schema migration replay,
receipt/effect evidence, backup restore correctness, p95 latency, recovery time,
cost and operational burden. Keep absolute values and failure cases; do not use
a model agreement or green source CI as a performance or deployment benchmark.

## Source and authority boundary

- Source present ≠ built ≠ installed ≠ live endpoint ≠ accepted consumer cutover.
- Human-reviewed architecture ≠ implementation. Unit fixtures ≠ production probe.
- PostgreSQL `READ ONLY` transactions do not make privileged SQL functions safe;
  enforce least-privilege roles, extension restrictions and function policy.
- The current `read_schemas` setting limits schema inventory, **not** arbitrary
  governed `SELECT` relation access; the database login's grants and function
  ACLs are the effective query boundary. Verify denial with a real DB account.
- A static service bearer is not end-user JWT/RLS isolation. Do not expose a
  Supabase-style public client API until per-user and per-object authorization
  is verified independently.
- No repository-wide SQL Connectome license is currently established. Review
  redistribution terms for every external component before packaging it.

Comparison sources: upstream `supabase/supabase` README and self-hosted Docker
documentation, plus this repository's `docs/ARCHITECTURE.md`,
`docs/THREAT_MODEL.md`, `docs/PROJECT_CONTROL_PLANE.md`, and `docs/RECOVERY.md`.
