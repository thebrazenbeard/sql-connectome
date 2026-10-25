# Provider-Neutral Connectivity V1

Status: APPROVED

## Goal
Separate connectivity mechanics from SQL semantics while preserving exact runtime, catalog, session, transport, and effect evidence.

## Architecture
A Connectome ConnectionAdapter opens a ConnectionSession. The session exposes immutable ConnectionIdentity and executes opaque SQL payloads into ExecutionResult receipts. Native DB-API drivers and ADBC are peer transports. JDBC/ODBC are optional bridges represented by the same contract when required; no transport receives semantic authority.

Connection capability does not imply parse, bind, translation, validation, authorization, or equivalence capability.

## Identity and receipts
ConnectionIdentity binds provider, engine, engine version, transport family, transport implementation/version, endpoint identity where safely representable, catalog/database, session facts, and capability declarations. Secrets are forbidden from serialized identities and receipts.

**Evidence class: `HOST_ASSERTED`.** The DB-API and ADBC adapter constructors receive these fields from the caller; constructing an identity after opening a connection does not independently verify the configured provider, engine name, endpoint, database, cluster, or role. For example, a genuine SQLite connection can be configured with a claimed PostgreSQL identity and receive that descriptor's stable digest. The native-driver type checks protecting read-only execution are a separate local effect control and do **not** upgrade the identity's provenance. An authenticated server/endpoint probe, TLS identity, and provider or database binding must be independently observed before a receipt can contribute to physical-runtime currentness. A connection identity digest proves consistency of the supplied descriptor, not its truth.

Execution receipts bind connection identity digest, SQL digest, effect class, success/error, native error evidence, row/column metadata where returned, and upstream semantic/validation/authorization receipt digests when supplied.

## Effect boundary
V1 distinguishes READ_ONLY, MUTATING, DDL, TRANSACTION_CONTROL, UNKNOWN. The connectivity layer never authorizes an effect. If no external authorization receipt is supplied, protected-effect execution is rejected by policy rather than inferred from SQL text.

Security hardening: the caller's `READ_ONLY` label alone does not confer a read-only execution boundary. The DB-API session conservatively admits only one syntactic SELECT and requires a supported native connection: SQLite uses `PRAGMA query_only=ON`, and Psycopg 3 PostgreSQL requires an idle connection and configures the next transaction read-only. Other DB-API drivers fail closed until separately qualified. This does not mitigate side effects of a privileged SELECT-invoked external function: review the database login's function, extension, and filesystem privileges independently.

A string `authorization_receipt` by itself is not a validated authorization. Protected executions now require a trusted host-injected `effect_authorizer(sql, effect, receipt, identity)` callback; absent or rejected validation fails closed. This callback is an explicit host trust boundary, not an authorization service provided by SQL Connectome. A production authorizer must verify issuer, actor, effect, SQL/target binding, expiry, and replay handling. No callback is configured by default, so protected execution is disabled by default.

Only qualified SQLite and Psycopg 3 sessions may execute externally authorized `MUTATING`/`DDL`, each from an idle writable connection. `TRANSACTION_CONTROL` and `UNKNOWN` are always unsupported: an opaque transaction command cannot independently prove effect completion. The adapter commits an authorized SQL effect before returning native success; commit failures are native errors, and the caller must establish externally whether the effect happened in an ambiguous transport failure. Read-only SELECTs roll back their native read-only transaction after fetching rows so subsequent SELECTs receive a new read-only boundary. These operations cannot be joined into a caller-managed multi-statement transaction through this narrow adapter.

## Adapters
- DBAPIAdapter: mechanical Python DB-API connection factory wrapper.
- ADBCAdapter: optional adapter behind lazy import/injected factory; absence of ADBC must not break core.
- JDBC/ODBC: contract-compatible future/optional adapters; no dependency added in V1 unless evidence requires one.

## Failure behavior
Connection failures and native execution errors remain native evidence. Unsupported capability is explicit. Session identity is assembled after connect from host-supplied fields; it is not actively re-attested after catalog/session changes, and must not be reused as proof of physical runtime currentness.

## Tests
Use fake DB-API connections plus SQLite for deterministic local execution. ADBC is tested through injected factories, not a network dependency.
