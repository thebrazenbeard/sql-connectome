# Lantern read gateway client V1 — opt-in source candidate

Status: **SOURCE-ONLY / NOT DEPLOYED / NOT AN AUTHORIZATION GRANT**.

`SQL_CONNECTOME_LANTERN_ROUTE=legacy_v4` remains the default. It uses the
historical direct `bt2` cut and view reads. This is incompatible with a separate
least-privilege reader role under BT2's V4 internal-schema assertion and must
not be promoted as a production consumer credential.

`SQL_CONNECTOME_LANTERN_ROUTE=gateway_v1` is an explicit, no-fallback candidate:

1. Only the exact scope `PROJECT_LANTERN` is admitted. A different requested
   scope fails before opening a connection.
2. In one PostgreSQL `REPEATABLE READ READ ONLY` transaction, SQL Connectome
   records logical runtime identity and executes exactly one bounded gateway
   query: `SELECT lantern_read.current_cut_v1() AS snapshot`.
3. The expected `snapshot` is PostgreSQL `jsonb` with `schema` equal to
   `BT2_LANTERN_READ_GATEWAY_V1`, `project_scope` equal to `PROJECT_LANTERN`,
   one canonical `cut` object and a current-profile/policy-only `payload` array.
4. `cut` retains V4 `facade_id=BT2_MATERIAL_CUT_V1`, profile, predecessor,
   policy, nonnegative integer material count and exact members. Each payload
   includes the V4 material fields plus `canonical_payload_pg_text`: the exact
   PostgreSQL `canonical_payload::text` used by the producer's digest algorithm.
   The client independently reparses this text, compares it to the returned
   JSON payload, then calculates SHA-256 over its UTF-8 bytes. The helper text
   is stripped before returning payload to callers.
   The decoder rejects duplicate JSON keys, Boolean/integer confusion,
   mismatched signed zero, and decimals that cannot survive the default
   binary64 JSONB loader's shortest-decimal round trip. This is a bounded
   precision-loss check, **not arbitrary-precision numeric fidelity**; a
   lossless typed-number output contract remains a separate qualification gate.
5. The client checks exact row count, ordered four-field members, scope,
   profile/policy binding and each canonical digest. The receipt binds the
   `gateway_v1` route and explicit gateway schema. Any mismatch aborts; there is
   no owner/direct-reader route or provider fallback on gateway failure.

This is a **client-side contract**, not a gateway implementation. The database
side must provide a hardened `STABLE SECURITY DEFINER` function in a dedicated
non-public schema, with a restricted NOLOGIN owner and separate LOGIN reader.
That reader may have schema `USAGE` and exact function `EXECUTE` only, never
`bt2` schema access or producer/write powers. BT2's frozen V4 schema and
`assert_internal_access_boundary_v1()` remain authoritative. The gateway must
filter old profile/policy materials *before* returning the cut payload, not
trust caller filters. Profile-lineage and negative ACL tests on PostgreSQL
16/17 are mandatory before any deployment consideration.

The source tests exercise the client under a fake connection. They **do not**
qualify the database gateway, real role grants, SSL endpoint identity, remote
MCP authentication, Project Lantern consumption, backup/recovery, or a
Supabase replacement. See BT2's `LANTERN_READ_ROLE_GATEWAY_ADR_V1.md` and
`docs/SUPABASE_REPLACEMENT_GATES.md`.
