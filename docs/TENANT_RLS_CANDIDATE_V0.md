# Tenant-bound RLS read: CI-only reference V0

This source is **not a public Auth service, generated API, or installed route**.
`tenant_rls_candidate.py` is not wired into REST, MCP, or the static operator
bearer. The opt-in function defaults disabled and queries only the disposable
`sql_connectome_rls_ci.tenant_documents` fixture.

The host must supply an independently trusted, signature-validating token
verifier. The candidate checks exact issuer, audience, UUID tenant, subject,
not-before and expiry after that verifier returns claims; it does **not**
implement a JWT verifier, key rotation, revocation, discovery/JWKS, or token
introspection. The unit-test verifier is intentionally synthetic evidence.
The read entrypoint uses the server clock and does not accept an untrusted
request-supplied clock override. The verifier and expected issuer/audience
must likewise remain server-controlled, never exposed as request parameters.

Real PostgreSQL 17 CI (explicit `SQL_CONNECTOME_TENANT_RLS_CI_EPHEMERAL=1`)
creates a new restricted LOGIN, a forced-RLS table, and a deny-by-default
tenant policy. It exercises A→B→A on one reused connection, empty policy scope,
cross-tenant permissive-policy drift, ADMIN-only role membership, privileged
role attributes, a post-bind database error and subsequent recovery. The CI
test intentionally demonstrates that issuing arbitrary SQL under the private
reader role can spoof the tenant GUC and access another tenant's rows: this
is a documented threat boundary, not an admitted API capability. Fixture
DDL and role changes are only admitted on the pinned disposable loopback CI
database and removed after each test.

The fixed SQL deliberately has **no tenant WHERE** so PostgreSQL RLS is really
exercised. The returned rows are independently checked against the verified
tenant: one foreign row fails the whole read. Transaction-local tenant context
is rolled back/committed before the connection can be reused.

**Hard boundary:** PostgreSQL custom GUCs are user-settable. Giving end users
the reader credential or arbitrary SQL access would let them spoof the tenant
context, despite RLS. Never expose the existing generic `query_readonly` on
this role; the tenant binding must remain in a private, fixed-query server path.
Successful CI will still **not** qualify a production issuer, dedicated cluster,
transport authentication, tenant provisioning, or a Supabase replacement.
