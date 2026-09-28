# Equivalence and Conformance Lab V1

Status: APPROVED

## Purpose

Create an evidence-producing laboratory for testing whether SQL programs and governed rewrites preserve observable behavior. Engine behavior is evidence, not semantic truth.

## Architecture

The lab has five independent evidence lanes: deterministic generated schema/data cases; metamorphic relations; SQLLogicTest-style corpus ingestion; provider-neutral differential execution; and bounded/formal evidence for explicitly modeled rewrite classes. SQLancer-style generation is an adversarial input source, not an oracle.

## Result States

A comparison produces MATCH, MISMATCH, INCONCLUSIVE, or UNAVAILABLE. MATCH is evidence only for the exact case/runtime/context. MISMATCH preserves both observations and does not automatically declare either engine incorrect.

## Comparison Semantics

V1 supports ordered row equality, bag equality, set equality only when explicitly declared, and native error-class comparison. NULL, type/value representation, floating point, collation/timezone, and nondeterministic functions are never silently normalized; insufficient policy yields INCONCLUSIVE.

## Evidence and Authority

Every case, execution observation, comparison, and qualification report has deterministic canonical serialization and digest. Receipts bind runtime identity plus catalog/session facts, schema/data seed/digest, SQL, result/error evidence, comparison policy, and upstream rewrite receipt where present. Existing semantic-loss markers are preserved. Rewrite definitions remain immutable; qualification is a separate artifact. Internal hostile review and independent-model review remain separate evidence lanes.

## Initial Scope

V1 qualifies the Step 5 redundant-project rule using deterministic SQLite and DuckDB executions already available locally, while defining provider-neutral runner interfaces for PostgreSQL/MySQL/MariaDB/Trino without changing comparison semantics. No network database is required for the core test suite.

## Failure Policy

Any mismatch is retained as a reproducible counterexample with seed and receipts. CI fails only when a case marked as a repository invariant regresses; exploratory/adversarial mismatches are recorded rather than erased.
