# Supabase Provider Observation Adapter V1

## Purpose

SQL Connectome may describe a Supabase project as one concrete PostgreSQL provider binding without making Supabase part of SQL semantics and without turning observation into provisioning authority.

This first slice is intentionally **observation-only**.

```text
Supabase Management project observation
    -> secret rejection
    -> provider-neutral PostgreSQL target proposal
    -> optional operator registration in SQL Connectome

OBSERVATION != REGISTRATION != PROVISIONING != PROVIDER EFFECT
```

## Evidence cut

Provider behavior was checked on 2026-10-07 against:

- current Supabase documentation for PostgreSQL projects, Management API project lifecycle, database branching, backups/PITR, and Supavisor;
- upstream `supabase/supabase@ccb1c601664168d301c5849ed0823ddd52dd4f1b`, shallow/sparse donor inspection of Studio project pause/restore and branch-create mutations;
- a read-only live Supabase inventory confirming that managed projects expose project ref, region, provider status, PostgreSQL engine/version/release-channel, and database host observations.

The live provider inventory is evidence for adapter shape only. Private project identifiers, credentials, and private state are not source-controlled here.

## Source contract

`sql_connectome.supabase_provider.SupabaseProjectObservation` accepts a Management-API-style project observation and emits arguments compatible with `register_database_target(...)`.

The proposal records:

- `provider_kind=supabase`;
- the non-secret project ref as `provider_resource_ref`;
- PostgreSQL as engine identity;
- provider region;
- mapped lifecycle state;
- observed provider/database metadata;
- `provider_observation_only=true`.

It does **not** call Supabase, create a project, pause/restore a project, create/merge/reset a branch, rotate a database password, alter pooler settings, run a migration, or change credentials.

Secret-bearing fields are rejected rather than copied into target metadata.

## Lifecycle mapping

The adapter maps known provider observations conservatively:

- `ACTIVE_HEALTHY -> RUNNING`
- creation/restore/upgrade states -> `PROVISIONING`
- paused/inactive states -> `STOPPED`
- explicitly unhealthy/degraded states -> `DEGRADED`
- any unrecognized future state -> `UNKNOWN`

Unknown provider vocabulary therefore does not get silently promoted to a healthy/running claim.

## Protected provider-effect frontier

A later Supabase provider-effect adapter is justified only if it adds governance that generic PostgreSQL execution does not already supply. Any such adapter must preserve the existing SQL Connectome control-plane requirements:

1. exact protected-effect authority for the target and operation;
2. stable request/idempotency identity where the provider supports it, otherwise explicit replay protection;
3. no plaintext provider credential persistence;
4. pre-effect subject binding;
5. provider-side post-effect readback;
6. append-only effect evidence that distinguishes request, attempt, effect, and verified effect;
7. ambiguous outcomes reconcile before retry;
8. provider identity never changes SQL semantic identity.

Potential future provider effects include project create/pause/restore, branch lifecycle, and provider configuration. They are deliberately outside V1.

## Recovery boundary

SQL Connectome's provider-independent `pg_dump` / blank-target `pg_restore` qualification remains the portable recovery baseline. Supabase daily backups and PITR may add provider-local recovery evidence, but they do not replace the portable archive contract.

Supabase Auth, Storage, Realtime, Edge Functions, and provider branching are useful platform capabilities. They are not PostgreSQL semantic identity and are not implied by registering a database target.
