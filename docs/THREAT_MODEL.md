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
- schema inventory allowlist;
- provider-neutral runtime identity digest;
- no HTTP write endpoint.

## Important residual risks

A SQL SELECT can invoke database functions. Therefore durable deployments MUST use a dedicated database login whose PostgreSQL privileges are themselves read-only and whose executable-function reachability is reviewed. Application parsing is defense in depth, not the final write boundary.

A static bearer token is acceptable only for the first private development slice. The ChatGPT-facing deployment should use a scoped machine identity/OAuth-style boundary with rotation and revocation.

postgres-meta, if later admitted, must remain behind the control plane. Its upstream project explicitly does not provide standalone security.

## Non-goals

V1 does not claim:
- public multi-tenancy;
- arbitrary untrusted SQL safety under an owner role;
- realtime delivery;
- end-user auth;
- provider high availability;
- qualified disaster recovery until restore tests exist.
