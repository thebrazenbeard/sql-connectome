# Equivalence and Conformance Lab V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic, provider-neutral behavioral equivalence evidence for SQL and governed rewrites.

**Architecture:** Separate case generation, execution observations, comparison, and qualification into immutable receipt-bearing artifacts. Use SQLite/DuckDB as deterministic V1 execution lanes while preserving a neutral runner contract for additional engines.

**Tech Stack:** Python 3.12, pytest, DuckDB, sqlite3, existing canonical_digest and rewrite receipt models.

## Global Constraints

Engine behavior is evidence, never universal truth. MATCH/MISMATCH/INCONCLUSIVE/UNAVAILABLE are explicit. Preserve native errors and semantic-loss markers. Bind runtime/catalog/session/schema/data/SQL/comparison policy into receipts. SQLancer-style generation is input, not oracle. Core CI has no network database dependency. No rewrite self-promotes qualification.

---

### Task 1: Immutable conformance artifacts
**Files:** create `src/sql_connectome/conformance.py`; test `tests/test_conformance.py`.
**Interfaces:** ConformanceCase, ExecutionObservation, ComparisonPolicy, ComparisonResult and deterministic digest functions.
- [ ] Add failing deterministic-digest and identity-binding tests; verify import failure.
- [ ] Implement frozen artifacts/canonical serialization; verify focused tests and Ruff; commit.

### Task 2: Neutral runner and deterministic SQLite/DuckDB lanes
**Files:** create `src/sql_connectome/conformance_runners.py`; extend `tests/test_conformance.py`.
**Interfaces:** runner exposes runtime identity and `execute(case, sql) -> ExecutionObservation`.
- [ ] Test identical seed execution, native errors, runtime/session receipt divergence.
- [ ] Implement isolated in-memory SQLite and DuckDB runners; verify focused tests/Ruff; commit.

### Task 3: Comparison and metamorphic qualification
**Files:** modify `src/sql_connectome/conformance.py`; create `src/sql_connectome/metamorphic.py`; test `tests/test_metamorphic.py`.
**Interfaces:** `compare_observations(left,right,policy)`; `qualify_rewrite(...)`.
- [ ] Test ordered/bag/set/error/inconclusive semantics.
- [ ] Implement exact policies without silent coercion.
- [ ] Qualify redundant-project cases on SQLite and DuckDB independently; preserve mismatches; verify; commit.

### Task 4: Corpus and adversarial generation boundaries
**Files:** create `src/sql_connectome/conformance_corpus.py`, `src/sql_connectome/adversarial_generation.py`; test `tests/test_conformance_corpus.py`.
**Interfaces:** SQLLogicTest-style records -> cases; deterministic seed-bound bounded generator.
- [ ] Test parser/generator determinism and unsupported constructs.
- [ ] Implement minimal statement/query ingestion plus integer/text/null generator; unsupported constructs become INCONCLUSIVE; verify; commit.

### Task 5: Hostile review and protected integration
**Files:** create `docs/reviews/2026-09-28-equivalence-conformance-lab-v1-hostile-review.md`.
- [ ] Attack oracle laundering, order/multiplicity, NULL/type normalization, nondeterminism, runtime identity drift, counterexample loss, and qualification overclaiming.
- [ ] Fix blocking findings with regression tests.
- [ ] Run `ruff check .` and `pytest`.
- [ ] Require exact-head protected checks, merge, and verify canonical main.

## Unresolved product decisions

None for V1. Broader formal solver choice and external corpus acquisition are intentionally deferred until the local evidence substrate is qualified.
