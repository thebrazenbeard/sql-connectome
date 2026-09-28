# Cross-Bound Authority and Provenance Receipts V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic cross-bound provenance and authority receipts for every SQL Connectome pipeline transition.

**Architecture:** Introduce an immutable receipt-DAG model that binds artifact digests, upstream receipts, evidence, semantic-loss accumulation, effect/authorization state, and optional Step 7 connection identity. Preserve the existing receipt helper as a compatibility envelope while keeping authorization external.

**Tech Stack:** Python 3.12, dataclasses, enum, hashlib/canonical JSON through existing `receipts.py`, pytest, Ruff.

## Global Constraints
Preserve UNDERSTAND != BIND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE. Never manufacture authorization. Preserve unknown/stale identity and semantic loss. Deterministic transition identity must not depend on wall-clock time. Existing receipt schemas remain valid.

---

### Task 1: Cross-bound receipt artifact
**Files:** Create `src/sql_connectome/cross_bound_receipts.py`; create `tests/test_cross_bound_receipts.py`.
**Interfaces:** `TransitionKind`, `CurrentnessState`, `AuthorityBinding`, `CrossBoundReceipt`, `cross_bound_receipt_digest()`, `make_cross_bound_receipt()`.
- [ ] Add failing tests for deterministic digest, changed input/output/upstream/evidence causing digest divergence, and timestamp-independent transition identity.
- [ ] Implement frozen canonical artifacts and deterministic serialization.
- [ ] Run focused pytest and Ruff.

### Task 2: Semantic-loss accumulation and chain validation
**Files:** Modify cross-bound module/tests.
**Interfaces:** `accumulate_semantic_loss(upstream, delta)`, `validate_receipt_chain(receipt, upstream)`.
- [ ] Test inherited loss cannot disappear, stable de-duplication, missing upstream rejection, mismatched accumulated loss rejection.
- [ ] Implement append-only accumulation and fail-closed chain validation.
- [ ] Run focused tests/Ruff.

### Task 3: Connection/catalog/session and authorization binding
**Files:** Modify cross-bound module and `src/sql_connectome/connectivity.py`; extend connectivity/cross-bound tests.
**Interfaces:** optional `ConnectionIdentity`, `EffectClass`, external authorization receipt; connectivity execution can bind an EXECUTE receipt without authorizing itself.
- [ ] Test catalog/session digest divergence, UNKNOWN currentness, protected-effect rejection without authorization, READ_ONLY without authorization.
- [ ] Implement identity snapshot/digest binding and protected-effect checks.
- [ ] Verify focused tests/Ruff.

### Task 4: Pipeline-stage helpers and compatibility
**Files:** Modify `src/sql_connectome/receipts.py`; create `src/sql_connectome/pipeline_receipts.py`; create `tests/test_pipeline_receipts.py`.
**Interfaces:** UNDERSTAND/BIND/TRANSLATE/VALIDATE/EXECUTE helpers delegate to one cross-bound constructor; legacy `make_receipt` unchanged.
- [ ] Test complete five-stage DAG and legacy receipt stability.
- [ ] Implement without stage-specific authority shortcuts.
- [ ] Verify focused/integration tests.

### Task 5: Hostile review and protected integration
**Files:** Create `docs/reviews/2026-09-28-cross-bound-authority-provenance-v1-hostile-review.md`.
- [ ] Attack receipt substitution, upstream omission, loss laundering, identity drift, authorization laundering, nondeterministic digest contamination, replay ambiguity, false signature claims.
- [ ] Fix blocking findings with regression tests.
- [ ] Run `ruff check .` and full `pytest`.
- [ ] Require exact-head CI, container smoke, Conformance Snapshot, Dependency Review, and CodeQL before merge.

## Unresolved product decisions
None for V1. Signing/key custody, nonce/replay policy for distributed deployments, and external transparency logs remain intentionally outside V1.