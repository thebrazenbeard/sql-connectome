# Dialect Genome Acquisition and Currentness V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add versioned, independently sourced dialect evidence and deterministic currentness reconciliation.

**Architecture:** Model dependency metadata, official documentation, and engine probes as immutable observations; reconcile them into claim-level artifacts without erasing disagreement. Build deterministic genome snapshots that can feed Step 8 evidence references.

**Tech Stack:** Python 3.12, dataclasses/enums, existing canonical digest machinery, pytest, Ruff.

## Global Constraints
Evidence classes remain independent. Version mismatch/staleness/unknown remain explicit. No observation class becomes semantic truth. No network or credential requirement in core CI.

---

### Task 1: Evidence observations and deterministic digests
Create `src/sql_connectome/dialect_genome.py` and `tests/test_dialect_genome.py`. Define EvidenceClass, EvidenceCurrentness, DialectObservation and digest. Test source/version/value divergence.

### Task 2: Claim reconciliation
Add ReconciliationState and DialectClaimReconciliation. Reconcile observation sets into AGREES/CONFLICTS/INSUFFICIENT/STALE while preserving every observation digest. Test contradictory docs/probes and version mismatch.

### Task 3: Genome snapshots
Add DialectGenome with target dialect/version, acquisition policy version, observations/reconciliations and deterministic digest. Reject observations for another dialect; preserve version-mismatched evidence explicitly.

### Task 4: Acquisition boundaries
Create `src/sql_connectome/dialect_acquisition.py` with constructors for dependency metadata, official-doc evidence, and engine-probe evidence. No fetching inside constructors. Test exact source locator/digest and probe runtime/version binding.

### Task 5: Receipt integration, hostile review, protected merge
Add genome/reconciliation evidence refs to pipeline tests without changing Step 8 schema. Hostile-review authority laundering, stale evidence, version aliasing, conflict erasure, source substitution, and timestamp-currentness confusion. Run Ruff/full pytest and all protected exact-head checks before merge.

## Unresolved product decisions
None for V1. Automated remote refresh scheduling and vendor-specific probe catalogs remain future acquisition jobs built on this substrate.
