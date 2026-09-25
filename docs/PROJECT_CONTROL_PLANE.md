# SQL Connectome Project Control Plane V1

## Purpose

The project control plane gives SQL Connectome a provider-neutral unit of database ownership and
lifecycle without making any cloud provider part of SQL semantics.

A **project** is a durable logical container. A **database target** is one concrete engine/provider
binding associated with that project.

V1 defines no credential fields. Database passwords, access tokens, private keys, and connection URIs must remain outside the control-plane data model; only non-secret references belong in its metadata.

## Data model

`sql_connectome.projects` records:

- stable project key;
- display name;
- lifecycle state;
- non-secret metadata;
- creation/update timestamps.

`sql_connectome.database_targets` records:

- project-local target key;
- target role: primary, replica, analytics, or archive;
- engine identity;
- provider kind;
- opaque non-secret provider resource reference;
- database name;
- optional region;
- observed lifecycle state;
- declared capabilities;
- non-secret metadata.

Only one non-retired PRIMARY target may exist per project.

Provider name, provider resource ID, cloud, and region are descriptive infrastructure metadata.
They do not alter SQL Connectome semantics and may change as infrastructure moves.

## Read surface

Authenticated read-only endpoints:

```text
GET /v1/projects
GET /v1/projects/{project_key}
```

Responses carry a receipt bound to the current PostgreSQL runtime identity.

## Operator write surface

V1 intentionally does not expose project or target creation through HTTP or MCP.

Operator-only registration:

```bash
python scripts/register_project.py \
  --project-key example \
  --display-name "Example"

python scripts/register_database_target.py \
  --project-key example \
  --target-key primary \
  --provider-kind external-postgresql \
  --provider-resource-ref provider-resource-id \
  --database-name app \
  --lifecycle-state RUNNING
```

Both commands require `SQL_CONNECTOME_DATABASE_URL` and execute directly against the governed
database. Each invocation appends an effect receipt. Replaying an exact registration is
idempotent and records `ALREADY_REGISTERED`; reusing a key for a different subject fails closed.

## Receipt integrity

Migration `0002_project_control_plane.sql` makes `sql_connectome.effect_receipts` append-only.
UPDATE and DELETE are rejected by a database trigger.

Receipts prove what the control plane recorded. They do not prove a provider API effect occurred
unless separate provider-side readback is included in the result evidence.

## Authority boundary

Registration is not provisioning.

A database target with lifecycle state `RUNNING` is an observed/declared control-plane fact, not
proof that SQL Connectome itself created the provider resource.

Future provisioning adapters must preserve:

1. explicit effect authority;
2. provider request idempotency;
3. no plaintext secret persistence;
4. provider-side post-effect readback;
5. a receipt binding requested subject to observed result;
6. semantic independence from provider identity.
