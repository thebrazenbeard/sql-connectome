# Receipt Occurrence and Trust Envelope V1

## Decision
Keep CrossBoundReceipt as deterministic semantic/provenance identity. Add a separate occurrence envelope for event identity, replay policy, and optional cryptographic authenticity.

An OccurrenceEnvelope binds receipt_digest, occurrence_id, issued_at, nonce, signer_id, signature_algorithm, and signature. Its occurrence digest includes occurrence metadata and therefore does not replace the deterministic receipt digest.

V1 trust verification is algorithm-agile through an injected verifier protocol. Core SQL Connectome does not own keys and does not manufacture signatures. UNSIGNED envelopes remain valid provenance occurrences but are not authenticated. A TrustPolicy can require a signature and an allowed signer. ReplayGuard is an injected/storeable protocol; the in-memory implementation is process-local and qualification-only.

Fail closed when policy requires authentication and signer/signature/verifier is absent, signer is not allowed, signature verification fails, or the occurrence digest has already been accepted by the replay guard.

No claim: signatures establish authorization. Authorization remains a separate Step 8 binding.