# Existing PostgreSQL target: operator admission V1

`scripts/admit_postgres_target.py` is a **read-only, operator-side preflight** for
an already-provisioned PostgreSQL 16+ PRIMARY target. It does not create a
database, change a grant, register a target, deploy an endpoint, copy data,
declare Project Lantern current, or authorize a consumer cutover.

## Operator inputs

- `SQL_CONNECTOME_DATABASE_URL`: read-capable **registry** connection URI.
- `SQL_CONNECTOME_TARGET_DATABASE_URL`: restricted **target** connection URI.
- Both connection strings must explicitly specify `sslmode=verify-full`, a
  single hostname, and an existing `sslrootcert` file. The configured target
  hostname must equal `--expected-host`. Credentials must be supplied through
  the operator environment, never command-line arguments or control-plane metadata.
- Registry project and PRIMARY target must already exist with `RUNNING` state.
  Supply exact non-secret provider kind and resource reference for comparison.
- Pin the expected target database/user, PostgreSQL physical system identifier,
  SQL Connectome migration version/checksum, and BT2 material-cut profile/policy
  digests independently of the current target observation.

Example flags (replace all identifiers and digests with reviewed values):

```bash
python scripts/admit_postgres_target.py \
  --project-key bt2 --target-key primary \
  --expected-provider-kind external-postgresql \
  --expected-provider-resource-ref reviewed-resource-id \
  --expected-host postgres.example.test \
  --expected-database bt2 --expected-user bt2_read \
  --expected-system-identifier 1234567890123456789 \
  --expected-migration-version 0002 \
  --expected-migration-checksum REVIEWED_CHECKSUM \
  --expected-profile-digest REVIEWED_PROFILE_DIGEST \
  --expected-policy-digest REVIEWED_POLICY_DIGEST
```

Exit codes are `0` for bounded `PASS`, `2` for observed/configured `FAIL`, and
`3` for `UNKNOWN`. The JSON receipt includes only status/check codes and
digests of pinned expectations. It excludes connection URLs, credentials,
hostnames, database roles, resource IDs, and raw driver exception messages.

## Evidence and denial

After registry cross-binding, the target connection establishes a repeatable-read
read-only transaction with a locally constrained `pg_catalog, pg_temp` search path
and a 5-second statement limit (connection timeout also 5 seconds). It checks the
active backend in `pg_stat_ssl`, the actual login/database/version, privileged role
flags and both inherited and `SET ROLE`-eligible high-risk predefined memberships,
SQL Connectome migration-head checksum, and exact BT2 `material_cut_v1` facade,
requested scope, profile, policy, and nonempty count. The V4 facade receives scope
as an argument; its result does not have a `project_scope` field. Finally it reads
`pg_control_system().system_identifier` and compares the independently pinned
physical cluster identifier.

The registered target is read twice, before and after the target probe, using
separate read-only snapshots. An observed change produces `UNKNOWN`. This B0/B1
comparison does not prevent an ABA change that returns to the original values
between observations; a locked registry or durable version/pin is a separate
cutover prerequisite.

A least-privileged PostgreSQL login may lack permission to execute
`pg_control_system()`. In that case admission is **UNKNOWN**; this CLI will
never grant itself privilege or elevate roles. A separately governed operator
may grant the narrow function privilege if acceptable to the security model.
An absent or wrong facade/migration, privileged role, mismatched identity, or
inactive TLS is `FAIL`. Unavailable network/driver/probe evidence is `UNKNOWN`.

The configured `verify-full` and observed `pg_stat_ssl` results establish TLS
configuration and the server's view of TLS. They are not a returned peer
certificate fingerprint; host/CA trust must be established independently.
The registry provider resource reference is descriptive metadata, not proof of
provider ownership. The physical system identifier narrows cluster ambiguity,
but cannot prove a specific hosted account or the complete data contents.

Only *selected role flags and memberships* are inspected. Ordinary PostgreSQL
grants, default privileges, executable functions, row-level security policies,
and `SECURITY DEFINER` reachability are **not audited by this CLI**. Every receipt
therefore says `database_grants_state=UNKNOWN` and
`database_grants_qualified=false`, including on PASS.

**Even a PASS is only `OPERATOR_READONLY_TARGET_ADMISSION` evidence.** It is not
authenticated MCP transport qualification, data/role/ACL parity, full Lantern
payload qualification, restore qualification, continuous freshness, or deployment
authority. Continue with the gates in `SUPABASE_REPLACEMENT_GATES.md`.
