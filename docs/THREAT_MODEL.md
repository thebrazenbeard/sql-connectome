# SQL Connectome V1 Threat Model

## Protected assets

- database contents;
- credentials and service identities;
- migration lineage;
- Lantern material/provenance state;
- effect receipts;
- provider configuration.

## V1 controls

- bearer authentication on every `/v1/*` route;
- no owner/database credential returned by any API;
- raw query endpoint accepts one SELECT statement only;
- database executes reads in a READ ONLY transaction;
- bounded statement timeout;
- bounded result row count;
- SQL text is capped at 50,000 characters and SQLGlot parsing at 10,000 AST nodes;
- schema inventory allowlist;
- provider-neutral runtime identity digest;
- no HTTP write endpoint;
- PostgreSQL engine validation uses `EXPLAIN` without `ANALYZE` inside a READ ONLY transaction;
- backup archives are SHA-256 bound to canonical manifests;
- restore requires explicit trusted-source acknowledgement and a blank target;
- restore is single-transaction, exit-on-error, and never performs clean/drop behavior;
- post-restore catalog and migration state are cross-bound to the backup manifest.

## Important residual risks

A SQL SELECT can invoke database functions. Planning may also evaluate some expressions, so `EXPLAIN` is not treated as a zero-risk sandbox. Therefore durable deployments MUST use a dedicated database login whose PostgreSQL privileges are themselves read-only and whose executable-function/extension reachability is reviewed. Application parsing and non-ANALYZE EXPLAIN are defense in depth, not the final write boundary.

A static bearer token is acceptable only for the first private development slice. The ChatGPT-facing deployment should use a scoped machine identity/OAuth-style boundary with rotation and revocation.

postgres-meta, if later admitted, must remain behind the control plane. Its upstream project explicitly does not provide standalone security.

A valid backup checksum establishes integrity, not trust. PostgreSQL restores may execute code
contained in a dump, so untrusted archives remain unsafe even when their manifests verify. The V1
restore CLI therefore requires an explicit trusted-source acknowledgement.

## Non-goals

V1 does not claim:
- public multi-tenancy;
- arbitrary untrusted SQL safety under an owner role;
- realtime delivery;
- end-user auth;
- provider high availability;
- cryptographic signing/authentication of backup manifests;
- automatic backup retention or remote object-storage lifecycle;
- cluster-global role/tablespace recovery.
