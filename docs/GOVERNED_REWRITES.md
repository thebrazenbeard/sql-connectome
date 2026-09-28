# Governed Rewrite Plan V1

SQL Connectome treats a rewrite recommendation as a governed claim, not as proof that two SQL programs are behaviorally equivalent.

Each selected rewrite has a stable versioned identity, required evidence, observed evidence, target-capability preconditions, unresolved semantic conditions, and a qualification state: `QUALIFIED`, `CONDITIONAL`, or `UNQUALIFIED`. Unknown rewrite rules fail closed as `UNQUALIFIED`.

Required evidence and observed evidence are separate. Merely naming an evidence source does not satisfy it. Translation integrates rewrite governance only after the target SQL has been generated and successfully parsed; type-semantic assessment is likewise recorded only after it has run.

Rewrite governance grants no execution authority. Every V1 artifact states `behavioral_equivalence = NOT_ESTABLISHED`. Conditional rewrites retain their unresolved semantic ceiling even when target parsing and engine validation succeed.

The governance digest is included in PostgreSQL translation-qualification evidence and receipts so the rewrite decision cannot change without changing the qualified evidence subject.
