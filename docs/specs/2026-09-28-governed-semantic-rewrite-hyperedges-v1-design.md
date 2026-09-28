# Governed Semantic Rewrite Hyperedges V1

Status: APPROVED BY EXECUTION MANDATE

## Goal

Represent semantic rewrites as deterministic, evidence-bearing hyperedges that operate on LogicalPlan artifacts without mutating the source-shaped SQLSemanticIR or conflating structural applicability with behavioral equivalence.

## Model

A rewrite definition is a separate immutable artifact with:
- rewrite_id and version
- consumed relation/expression IDs
- produced relation/expression descriptors
- preconditions
- postconditions
- evidence references
- counterexamples
- semantic_loss_delta
- authority ceiling
- provenance

A rewrite application binds:
input_plan_digest -> rewrite_definition_digest -> output_plan_digest.

## States

Applicability is explicit:
- APPLICABLE
- NOT_APPLICABLE
- UNRESOLVED

Qualification is separate:
- STRUCTURAL_ONLY
- BEHAVIORALLY_QUALIFIED
- FORMALLY_QUALIFIED

V1 only establishes deterministic structural qualification. No structural rewrite can upgrade itself to behavioral or formal equivalence.

## Invariants

- UNKNOWN evidence remains UNKNOWN; unresolved preconditions never silently pass.
- Counterexamples are first-class and preserved.
- semantic_loss_delta is append-only and cannot erase existing plan losses.
- Source/bound/schema digests remain bound through the output plan.
- Rewrites may consume or produce multiple relations/expressions.
- Deterministic serialization and digesting are required.
- Failed postconditions invalidate the application.
- No rewrite directly authorizes execution or protected effects.

## Initial V1 Rewrite

Introduce a narrowly scoped redundant-project-elimination example over LogicalPlan:
- consumes PROJECT whose input schema is field-for-field identical
- requires same ordering, field IDs, types, nullability, provenance, multiplicity, cardinality
- produces the input relation as replacement root/reference
- records no semantic-loss reduction unless independently evidenced
- refuses application if any required identity fact is missing or divergent

This example exists to qualify the governance substrate, not to claim a general SQL optimizer.
