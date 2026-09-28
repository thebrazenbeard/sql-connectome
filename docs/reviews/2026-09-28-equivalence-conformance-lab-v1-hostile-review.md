# Equivalence and Conformance Lab V1 — Internal Hostile Review

Reviewed implementation lineage through `f470d18cd54fa226b0945d7f4bf95931907c6b0f`.

## Attacks

1. Oracle laundering: cross-engine agreement must not become universal truth. The implementation only emits case-bound qualification.
2. Ordering/multiplicity: ordered, bag, and set policies are separate; bag comparison preserves duplicate counts.
3. Silent coercion: values are canonicalized exactly for comparison; no numeric/text/NULL coercion is introduced.
4. Nondeterminism: explicitly marked nondeterministic policies yield INCONCLUSIVE.
5. Runtime identity drift: execution observations bind EngineRuntimeIdentity and session facts.
6. Counterexample loss: non-MATCH engine results are retained with observation digests.
7. Qualification overclaim: successful reports say BEHAVIORALLY_QUALIFIED_CASE_BOUND, not universal equivalence.
8. Corpus authority: SQLLogicTest-style expectations are preserved as corpus evidence; unsupported records are marked unsupported rather than interpreted.
9. Generator authority: deterministic generation is explicitly tagged with no-oracle assumptions.

## Finding

SURVIVES_NARROWED.

V1 is intentionally not a full SQLLogicTest parser, SQLancer implementation, or formal verifier. It establishes the evidence substrate and deterministic local differential lanes those systems can feed. External corpus breadth and formal solver selection remain later qualification work, not implied capability.

Independent-model review: NOT PERFORMED. This is internal hostile review only.
