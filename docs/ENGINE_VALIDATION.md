# Engine Validation

SQL Connectome engine validation V1 adds a provider-neutral result and receipt envelope while preserving engine-specific validation evidence.

MySQL and MariaDB are independent adapters. Both V1 adapters use `EXPLAIN FORMAT=JSON` for admitted read-only SQL, but their native JSON payloads are opaque and are never treated as a shared plan schema. MySQL runtime identity includes the explain JSON format version when available. MariaDB is independently identified and never uses `ANALYZE FORMAT=JSON`.

Trino uses `EXPLAIN (TYPE VALIDATE)`. Catalog and schema identity are receipt-bound because validation depends on connected metadata and connector behavior.

These remote validators never install caller-supplied schema context or emit schema DDL. Schema context is evidence included in the deterministic receipt. A missing runtime is `UNAVAILABLE`; there is no cross-engine fallback.

Current qualification is `PROTOCOL_TESTED`: deterministic fake/protocol connection tests establish SQL Connectome adapter behavior, not real-engine behavioral equivalence. Real-engine qualification remains independent for mysql, mariadb, and trino.

Connectivity generalization through ADBC/JDBC/ODBC is deliberately deferred to ordered program step 7.
