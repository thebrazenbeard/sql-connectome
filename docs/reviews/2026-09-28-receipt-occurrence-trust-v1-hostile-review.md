# Receipt Occurrence and Trust Envelope V1 — Internal Hostile Review

Reviewed lineage through 5bacea58cd8061eedd02effd2df8ee006bbc74a3.

Attacks:
1. Semantic digest contamination: occurrence metadata is separate from CrossBoundReceipt and cannot change its deterministic digest.
2. Signature = authorization confusion: explicitly rejected; authenticity and execution authorization remain separate.
3. Missing signer/verifier: signature-required policy fails closed.
4. Trust-root bypass: allowed_signers rejects identities outside policy before verifier acceptance.
5. Replay: injected ReplayGuard can reject an already accepted occurrence digest; built-in guard is process-local only.
6. Fake crypto claim: core provides no signing implementation and makes no security claim for test verifiers.
7. Timestamp authority: issued_at is bound occurrence metadata but is not independently trusted time.
8. Distributed replay overclaim: NOT PROVIDED by in-memory guard.

Finding: SURVIVES_NARROWED.
Claim ceiling: algorithm-agile trust-policy and replay interfaces with deterministic occurrence binding. Production key custody, concrete cryptographic provider selection, trusted timestamping, and distributed durable replay storage remain external integrations.
Independent-model review: NOT PERFORMED.
