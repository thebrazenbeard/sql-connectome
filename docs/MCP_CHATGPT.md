# SQL Connectome MCP / ChatGPT Surface

## Status

This is the first source-controlled MCP surface for SQL Connectome.

It uses the current MCP Python SDK v2 and Streamable HTTP. The MCP server is a separate interface
over the same internal semantic and PostgreSQL control functions used by the REST API.

The endpoint path is `/mcp`.

## Invariants

The MCP surface preserves the core SQL Connectome separation:

`UNDERSTAND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`

Connecting or installing the MCP surface does not grant protected database-write authority.

The current MCP tool set exposes:

- runtime health and schema inventory;
- dialect inventory and evidence-based dialect probing;
- semantic parsing, expression-contract inspection, and schema binding;
- translation planning and guarded transpilation;
- PostgreSQL read-only EXPLAIN validation;
- hardened in-memory DuckDB EXPLAIN validation against caller-supplied schema context;
- end-to-end translation-to-PostgreSQL qualification;
- bounded PostgreSQL SELECT execution;
- migration-state inspection;
- Lantern current-cut reads.

It exposes no migration-apply, DDL, DML, restore, credential, role-management, or arbitrary owner-SQL
tool.

## Transport

Run the source-controlled entrypoint:

```bash
sql-connectome-mcp
```

The server uses Streamable HTTP, stateless mode, JSON responses, and the configured host/port. The
default local bind is `127.0.0.1:8001`, producing:

```text
http://127.0.0.1:8001/mcp
```

A public ChatGPT-facing deployment must use HTTPS.

## Authentication

Network deployment fails closed unless all three are configured:

- `SQL_CONNECTOME_MCP_RESOURCE_URL`
- `SQL_CONNECTOME_MCP_ISSUER_URL`
- `SQL_CONNECTOME_MCP_STATIC_TOKEN`

The current source includes a constant-time static-token verifier only as a private/bootstrap
resource-server mechanism. It advertises the configured resource and required scope through MCP
authorization metadata.

A durable public deployment should replace static-token verification with a real OAuth 2.1
authorization server, JWT verification, or RFC 7662 token introspection. The SQL Connectome tool
surface does not need to change when that verifier is replaced.

## Plugin package

`plugins/chatgpt/` contains the source for the SQL Connectome ChatGPT plugin behavior package.

That package is intentionally not treated as proof of connectivity. Its skill requires a live
SQL Connectome MCP connection before claiming that any SQL Connectome tool call was made.

The plugin package and the MCP endpoint are separate artifacts:

```text
ChatGPT plugin behavior package
        |
        v
connected SQL Connectome MCP resource
        |
        v
semantic plane + governed PostgreSQL read substrate
```

## Qualification

The MCP slice is qualified in-process with the official MCP client so tests exercise real MCP
tool discovery and calls rather than calling Python functions directly.

CI also exercises one database-backed MCP call against PostgreSQL 17 and one embedded DuckDB validation call through the official MCP client. HTTP/OAuth deployment
qualification remains a separate state until a concrete HTTPS deployment and authorization server
are bound and tested.

## Hosting

The source container supports both REST and MCP processes. For MCP hosting set
`SQL_CONNECTOME_PROCESS=mcp`; the container entrypoint maps the platform `PORT` to the MCP
listener and binds it to `0.0.0.0`.

Managed PostgreSQL hosts may inject a database URI plus a base64 project CA. SQL Connectome
normalizes that input into certificate-verifying `verify-full` TLS before creating database
connections. See `HOSTING.md`.

A deployable container is not the same as a deployed or qualified endpoint.
