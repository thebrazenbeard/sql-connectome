# Cross-Bound Authority and Provenance Receipts V1 — Internal Hostile Review

Reviewed exact implementation lineage through `7aa8fecff0c8d2dc07028ec4617d4e0f7d65474a`.

## Attacks

1. Receipt substitution: transition digests bind transition kind, exact input/output artifact digests, upstream receipt digests, evidence refs, implementation identity, authority, identity/currentness, and semantic loss.
2. Upstream omission: `validate_receipt_chain` requires exact ordered upstream receipt digests.
3. Loss laundering: accumulated semantic loss is recomputed from upstream receipts plus local delta; inherited markers cannot be silently removed.
4. Identity drift: execution receipts bind both the Step 7 connection identity digest and its materialized catalog/session/provider/transport snapshot.
5. Authorization laundering: protected EXECUTE effects require an externally supplied authorization receipt; receipt creation never creates authorization.
6. Nondeterministic digest contamination: deterministic transition identity contains no timestamp or random nonce.
7. Replay ambiguity: V1 transition identity intentionally represents semantic identity, not uniqueness of an execution occurrence. Replay/nonces remain a future envelope concern and are not claimed solved.
8. False signature claims: V1 provides SHA-256 tamper-evident canonical digests only; no cryptographic signer identity or key custody is claimed.
9. Currentness promotion: UNKNOWN and STALE are explicit states and receipt construction does not promote them.
10. Compatibility regression: legacy SQL_CONNECTOME_RECEIPT_V1 remains unchanged and has a regression test.

## Finding

SURVIVES_NARROWED.

The receipt DAG is suitable as a deterministic provenance and authority-binding substrate. It is not a signature system, distributed anti-replay protocol, or independent proof of semantic correctness.

Independent-model review: NOT PERFORMED. This is internal hostile review only.
