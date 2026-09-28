# Provider-Neutral Connectivity V1

Status: APPROVED

## Goal
Separate connectivity mechanics from SQL semantics while preserving exact runtime, catalog, session, transport, and effect evidence.

## Architecture
A Connectome ConnectionAdapter opens a ConnectionSession. The session exposes immutable ConnectionIdentity and executes opaque SQL payloads into ExecutionResult receipts. Native DB-API drivers and ADBC are peer transports. JDBC/ODBC are optional bridges represented by the same contract when required; no transport receives semantic authority.

Connection capability does not imply parse, bind, translation, validation, authorization, or equivalence capability.

## Identity and receipts
ConnectionIdentity binds provider, engine, engine version, transport family, transport implementation/version, endpoint identity where safely representable, catalog/database, session facts, and capability declarations. Secrets are forbidden from serialized identities and receipts.

Execution receipts bind connection identity digest, SQL digest, effect class, success/error, native error evidence, row/column metadata where returned, and upstream semantic/validation/authorization receipt digests when supplied.

## Effect boundary
V1 distinguishes READ_ONLY, MUTATING, DDL, TRANSACTION_CONTROL, UNKNOWN. The connectivity layer never authorizes an effect. If no external authorization receipt is supplied, protected-effect execution is rejected by policy rather than inferred from SQL text.

## Adapters
- DBAPIAdapter: mechanical Python DB-API connection factory wrapper.
- ADBCAdapter: optional adapter behind lazy import/injected factory; absence of ADBC must not break core.
- JDBC/ODBC: contract-compatible future/optional adapters; no dependency added in V1 unless evidence requires one.

## Failure behavior
Connection failures and native execution errors remain native evidence. Unsupported capability is explicit. Session identity is captured after connect and cannot be silently reused across a changed catalog/session.

## Tests
Use fake DB-API connections plus SQLite for deterministic local execution. ADBC is tested through injected factories, not a network dependency.
