# Session and Catalog Re-attestation V1

## Decision
Add a deterministic re-attestation artifact between provider-neutral connectivity and execution receipts. A session identity observed at open is not assumed current after arbitrary statements.

A SessionAttestation binds the prior connection identity digest, newly observed connection identity digest, catalog/session fact snapshot, attestation mechanism, evidence refs, and a continuity state: CONTINUOUS, DRIFTED, or UNKNOWN. Equality of independently observed identity snapshots establishes continuity for the bounded observation only; it is not a lease or future-currentness promise.

Execution receipt currentness may be CURRENT only when backed by a CONTINUOUS attestation whose observed identity digest equals the execution identity digest. DRIFTED and UNKNOWN fail closed for claims requiring current identity.

Adapters remain provider-neutral. V1 defines the artifact and validation contract; provider-specific SQL for obtaining catalog/session facts remains in adapter/probe implementations.

Hostile targets: session mutation after open, catalog switch, version/endpoint substitution, forged CURRENT promotion, attestation replay, and confusing bounded observation with future validity.