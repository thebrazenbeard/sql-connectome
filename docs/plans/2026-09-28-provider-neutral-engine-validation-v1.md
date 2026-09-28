# Provider-Neutral Engine Validation V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add independently evidenced MySQL, MariaDB, and Trino read-only validation adapters behind one narrow provider-neutral result/receipt contract.

**Architecture:** A new neutral validation module owns deterministic result, runtime-identity, native-error, and receipt construction without interpreting engine-native plan structures. Three engine modules implement only their own validation mechanisms and accept injected protocol-compatible connections, keeping driver/connectivity generalization out of this step. Existing PostgreSQL, DuckDB, and SQLite behavior remains unchanged.

**Tech Stack:** Python 3.12, dataclasses/Protocol, existing SQL guard and receipt digest helpers, pytest, Ruff.

## Global Constraints

- `UNDERSTAND != BIND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`.
- MySQL, MariaDB, and Trino remain separate adapter/evidence identities.
- Validation never authorizes execution and all V1 modes set `query_executed=False`.
- Remote validation emits no schema DDL.
- MySQL/MariaDB use `EXPLAIN FORMAT=JSON`; Trino uses `EXPLAIN (TYPE VALIDATE)`.
- MySQL never uses `EXPLAIN ANALYZE`; MariaDB never uses `ANALYZE FORMAT=JSON`.
- Native plans/errors remain engine-namespaced and lossless where exposed.
- Runtime receipts bind SQL, schema-context evidence, engine/version, catalog/database/schema and semantic session identity.
- Missing driver/runtime is `UNAVAILABLE`, never fallback.
- No ADBC/JDBC/ODBC abstraction, plan normalization, write execution, logical IR, rewrite hyperedges, or equivalence-lab work in this step.

---

### Task 1: Neutral validation contract and deterministic receipts

**Files:**
- Create: `src/sql_connectome/engine_validation.py`
- Test: `tests/test_engine_validation.py`

**Interfaces:**
- Consumes: existing `canonical_digest` receipt helper.
- Produces: `ValidationStatus`, `EngineRuntimeIdentity`, `NativeEngineError`, `EngineValidationResult`, and `build_engine_validation_result(...)`.

- [ ] **Step 1: Add the focused failing test**

Assert deterministic serialization/receipt; distinct runtime/session/catalog identity changes receipt; native payload/error fields survive; status includes PASS/FAIL/UNAVAILABLE; behavioral-equivalence ceiling remains NOT_ESTABLISHED; query_executed is explicitly false.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_engine_validation.py`
Expected: import failure because neutral interfaces do not exist.

- [ ] **Step 3: Implement the minimum behavior**

Use frozen dataclasses and sorted immutable key/value identity facts. Receipt payload includes adapter ID, runtime digest, SQL digest, schema-context digest, validation mode, status, query-executed flag, evidence ceiling, and native error digest when present. Do not normalize native plan trees.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_engine_validation.py`
Expected: neutral contract tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m ruff check src/sql_connectome/engine_validation.py tests/test_engine_validation.py`
Expected: Ruff clean.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/engine_validation.py tests/test_engine_validation.py
git commit -m "feat: add neutral engine validation contract"
```

### Task 2: Independent MySQL and MariaDB validators

**Files:**
- Create: `src/sql_connectome/mysql_engine.py`
- Create: `src/sql_connectome/mariadb_engine.py`
- Test: `tests/test_mysql_engine.py`
- Test: `tests/test_mariadb_engine.py`

**Interfaces:**
- Consumes: neutral result builder; existing `ensure_read_only_sql`; injected connection exposing cursor/execute/fetch operations.
- Produces: `validate_mysql_readonly(sql, *, connection, schema_context=None)` and `validate_mariadb_readonly(sql, *, connection, schema_context=None)`.

- [ ] **Step 1: Add the focused failing tests**

With deterministic fake connections assert each adapter: calls only its runtime/session identity reads plus `EXPLAIN FORMAT=JSON <sql>`; never emits DDL; never calls ANALYZE; preserves native JSON payload opaque; returns independent adapter/engine IDs; binds MySQL explain-json-format version where supplied; preserves native numeric code/SQLSTATE/message on failure; returns UNAVAILABLE when connection is absent/unusable; rejects non-read-only SQL before engine calls.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_mysql_engine.py tests/test_mariadb_engine.py`
Expected: import failures because adapters do not exist.

- [ ] **Step 3: Implement the minimum behavior**

Keep separate modules and runtime-query sets. Shared mechanics may use the neutral result builder only. Treat schema_context as receipt evidence, never DDL. Catch engine exceptions without importing a mandatory vendor driver: inspect standard exposed attributes conservatively and preserve unknown fields as native metadata.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_mysql_engine.py tests/test_mariadb_engine.py`
Expected: independent adapter tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m pytest -q tests/test_engine_validation.py tests/test_mysql_engine.py tests/test_mariadb_engine.py tests/test_duckdb_engine.py tests/test_sqlite_engine.py && py -m ruff check .`
Expected: new validators and existing local validators pass; Ruff clean.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/mysql_engine.py src/sql_connectome/mariadb_engine.py tests/test_mysql_engine.py tests/test_mariadb_engine.py
git commit -m "feat: add independent mysql and mariadb validation"
```

### Task 3: Trino validation adapter

**Files:**
- Create: `src/sql_connectome/trino_engine.py`
- Test: `tests/test_trino_engine.py`

**Interfaces:**
- Consumes: neutral result builder, read-only guard, injected Trino-compatible connection.
- Produces: `validate_trino_readonly(sql, *, connection, schema_context=None)`.

- [ ] **Step 1: Add the focused failing test**

Assert exact validation statement `EXPLAIN (TYPE VALIDATE) <sql>`; no DDL or execution-analysis statement; PASS only for a truthy validation response; catalog/schema/session identity changes receipt; native Trino error fields survive; unavailable connection is explicit; read-only rejection happens before engine calls.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_trino_engine.py`
Expected: import failure because adapter does not exist.

- [ ] **Step 3: Implement the minimum behavior**

Read runtime/catalog/schema/session identity through injected connection/cursor facilities available to the adapter. Preserve connector/catalog identity as opaque facts. Return engine-native validation payload without distributed-plan interpretation.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_trino_engine.py`
Expected: Trino adapter tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m pytest -q tests/test_engine_validation.py tests/test_mysql_engine.py tests/test_mariadb_engine.py tests/test_trino_engine.py`
Expected: all V1 remote validation tests pass.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/trino_engine.py tests/test_trino_engine.py
git commit -m "feat: add trino validation adapter"
```

### Task 4: Qualification/docs and full compatibility gate

**Files:**
- Modify: `docs/specs/2026-09-28-provider-neutral-engine-validation-v1-design.md`
- Create: `docs/ENGINE_VALIDATION.md`
- Test: `tests/test_engine_validation.py`

**Interfaces:**
- Consumes: all three adapters and neutral contract.
- Produces: deterministic `engine_validation_manifest()` declaring adapter versions, evidence ceilings, and independent qualification states.

- [ ] **Step 1: Add the focused failing test**

Assert manifest lists mysql, mariadb, trino independently; no family-level qualification exists; each starts below real-engine behavioral qualification when only fake/protocol tests exist; digest changes when adapter version/evidence changes.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_engine_validation.py -k manifest`
Expected: failure because manifest is absent.

- [ ] **Step 3: Implement the minimum behavior**

Add manifest and documentation describing exact validation mechanisms, non-execution guarantee scope, runtime identity, native evidence preservation, unavailable behavior, independent qualification, and explicit step-7 connectivity non-goal.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_engine_validation.py -k manifest`
Expected: manifest tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m ruff check . && py -m pytest -q`
Expected: Ruff clean and repository suite passes except any already-documented platform-specific baseline failure. Then require protected GitHub CI on exact head before merge.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/engine_validation.py docs/specs/2026-09-28-provider-neutral-engine-validation-v1-design.md docs/ENGINE_VALIDATION.md tests/test_engine_validation.py
git commit -m "docs: qualify provider-neutral engine validation"
```

## Unresolved Product Decisions

None required for implementation. Real-engine credentials/runtimes are deliberately not required for V1 construction; their absence limits qualification evidence independently per adapter rather than blocking the contract.
