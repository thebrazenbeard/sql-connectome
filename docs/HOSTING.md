# SQL Connectome Hosting V1

SQL Connectome is provider-neutral at runtime. The container can run either the REST control surface
or the MCP surface without changing the semantic or database layers.

## Process selection

The image defaults to the REST API:

```text
SQL_CONNECTOME_PROCESS=rest
PORT=8080
```

For MCP:

```text
SQL_CONNECTOME_PROCESS=mcp
PORT=8001
SQL_CONNECTOME_MCP_RESOURCE_URL=https://example.test/mcp
SQL_CONNECTOME_MCP_ISSUER_URL=https://issuer.example.test/
SQL_CONNECTOME_MCP_STATIC_TOKEN=<secret bootstrap token>
```

The container exposes both 8080 and 8001. The selected process binds to `0.0.0.0` so a managed
container platform can route HTTPS traffic to it.

## Managed PostgreSQL integration

A host may provide either:

- `SQL_CONNECTOME_DATABASE_URL`; or
- `DATABASE_URL`.

If a base64 `PROJECT_CA_CERT` is also present, SQL Connectome writes the certificate to a
new randomly named, owner-only temporary file (mode `0600` on POSIX), strips any injected `sslmode` / `sslrootcert` query parameters from the
database URI, and replaces them with:

```text
sslmode=verify-full
sslrootcert=<process-private CA path>
```

This is the managed-host adapter boundary. Core database code continues to consume only
`SQL_CONNECTOME_DATABASE_URL`.

The generated CA file remains readable for PostgreSQL connections until normal process exit,
when SQL Connectome removes it if the file identity is unchanged. An explicitly supplied
`ca_path` must be absent in an existing directory: an existing file or symbolic link fails
closed without truncating its target, and explicit paths remain caller-managed. Repeated
configuration with the same explicit path therefore requires caller cleanup first. This
source-level safeguard does not protect against a same-UID attacker who can mutate a
process-owned temporary file, abnormal process termination, or hostile parent-directory races.

If the CA value is invalid, SQL Connectome fails closed before starting the application.

## Aiven

Aiven can inject a PostgreSQL service URI and `PROJECT_CA_CERT` through an application-service
integration. For an Aiven application deployment, bind the existing PostgreSQL service to the
application and use `SQL_CONNECTOME_DATABASE_URL` (or `DATABASE_URL`) as the integration
environment key.

The PostgreSQL service cloud and the application cloud are infrastructure choices, not SQL
Connectome semantics.

Aiven application hosting is not required by the project. The same image can run on any container
host that can provide:

1. outbound PostgreSQL connectivity;
2. HTTPS ingress;
3. environment/secret injection;
4. the MCP resource-server authentication settings when MCP is enabled.

## Qualification boundary

A green container/runtime test proves source behavior only. A public ChatGPT-ready deployment is a
separate qualification subject and requires:

- exact deployed source revision;
- HTTPS endpoint readback;
- successful MCP initialize/list-tools call;
- authorization challenge/token validation;
- database TLS verification;
- exact database runtime identity and migration-head readback;
- confirmation that protected write tools remain absent.

Plugin installation is another separate state and does not imply endpoint or database
qualification.
