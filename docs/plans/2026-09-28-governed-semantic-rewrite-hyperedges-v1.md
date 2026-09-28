# Governed Semantic Rewrite Hyperedges V1 Plan

1. Add failing tests for immutable rewrite definitions, deterministic digesting, and explicit applicability states.
2. Implement the rewrite hyperedge model and application receipt.
3. Add failing tests for multi-input/multi-output support, unresolved preconditions, counterexample preservation, and append-only loss accounting.
4. Implement deterministic structural application over LogicalPlan.
5. Add and qualify one redundant-project-elimination rewrite with strict field/schema identity preconditions.
6. Add hostile review focused on false equivalence, evidence laundering, loss erasure, ID instability, and source/bound/schema digest drift.
7. Run focused and full repository tests through protected CI.
8. Open PR, require exact-head green checks, merge through protections, and record canonical main head.
