# Provider-Neutral Connectivity V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox syntax.

**Goal:** Add provider-neutral connection/session/execution receipts without granting transports semantic or authorization authority.

**Architecture:** Immutable identity/effect/result artifacts plus a narrow adapter/session protocol. DB-API is the concrete local lane; ADBC is optional/injected.

**Tech Stack:** Python 3.12, pytest, sqlite3, existing canonical_digest/engine identity receipts.

## Global Constraints
No secret serialization. Transport capability != semantic capability. Connectivity never authorizes protected effects. ADBC remains optional. Native errors remain evidence.

### Task 1: Connectivity identity and session contract
Create `src/sql_connectome/connectivity.py`, test `tests/test_connectivity.py`.
Add red tests for deterministic identity digests, secret exclusion, effect classes, and upstream receipt binding; implement immutable artifacts/protocols; verify Ruff/tests.

### Task 2: DB-API adapter
Create `src/sql_connectome/dbapi_adapter.py`; extend tests.
Test isolated SQLite session identity, read-only execution, native error preservation, protected-effect rejection without authorization, and authorization receipt binding. Implement minimum adapter/session.

### Task 3: Optional ADBC boundary
Create `src/sql_connectome/adbc_adapter.py`; test injected factory behavior and unavailable dependency state without importing ADBC at core import time. No external database required.

### Task 4: Hostile review and integration
Review secret leakage, authority confusion, session/catalog drift, SQL classification overclaim, error laundering, and transport/semantic conflation. Fix findings, run full protected checks, merge, verify main.

## Unresolved product decisions
None for V1. Concrete JDBC/ODBC dependencies remain evidence-triggered rather than preinstalled.
