# Governed Semantic Rewrite Hyperedges V1 — Hostile Review

Exact reviewed head before narrowing: `add13a9da336ab5fdfc0aa28267b9402ea0f0bcd`.

## Attack

The redundant-project rule removed a PROJECT when its output schema equaled its input schema and relation properties matched. That is structurally attractive but the V1 LogicalPlan does not encode expression ownership strongly enough to prove that a projection carrying distinct field identities or project-local expression semantics is eliminable merely from display-equivalent schema data.

This creates a false-equivalence risk: a structurally valid output could preserve enough field IDs to pass graph validation while laundering uncertainty about which expression established those fields.

## Disposition

SURVIVES_NARROWED.

The rule is restricted to stable field identity: projected field IDs must already be exactly the input field IDs, in addition to full schema equality and matching scope/multiplicity/cardinality. V1 remains STRUCTURAL_ONLY and appends a rewrite-loss marker. It does not claim behavioral or formal equivalence.

Counterexamples and unresolved cases remain explicit. Step 6 is responsible for behavioral/differential/formal qualification.

Independent-model review: NOT PERFORMED in this review. This document is internal hostile review and must not be represented as independent corroboration.
