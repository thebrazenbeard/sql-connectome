# Cross-Bound Authority and Provenance Receipts V1

Status: APPROVED

## Purpose
Make every SQL Connectome pipeline boundary produce a deterministic, tamper-evident provenance artifact without collapsing semantic evidence, execution identity, or authorization into one authority decision.

## Architecture
V1 adds an immutable cross-bound receipt DAG above the existing canonical digest machinery. A receipt binds a transition kind, exact input/output artifact digests, upstream receipt digests, evidence references, implementation identity, authority/effect state, accumulated semantic-loss markers, and optional connection/catalog/session identity. Receipt creation is deterministic for deterministic inputs; runtime timestamps remain envelope metadata and are excluded from deterministic transition identity.

The transition model follows UNDERSTAND -> BIND -> TRANSLATE -> VALIDATE -> EXECUTE. Receipts may also bind governed rewrite and conformance evidence without treating those artifacts as authorization.

## Identity and Currentness
Execution-bound receipts bind the Step 7 ConnectionIdentity digest and a materialized snapshot of provider, engine/version, transport, endpoint identity, catalog, session facts, and capabilities. Missing identity fields remain null. Unknown or stale currentness is represented explicitly and cannot be promoted by receipt creation.

## Authority
Effect classification and authorization are separate fields. READ_ONLY transitions need no authorization receipt. MUTATING, DDL, TRANSACTION_CONTROL, and UNKNOWN execution transitions require an externally supplied authorization receipt. The receipt subsystem verifies presence/binding only; it never manufactures authorization.

## Semantic Loss
Each transition carries a semantic_loss_delta and accumulated_semantic_loss. Accumulation is append-only and deterministic: inherited markers are preserved in upstream order, then new markers are appended with stable de-duplication. A later stage cannot erase earlier uncertainty or loss.

## Integrity
Each transition has a deterministic transition_digest computed from semantic content. An optional envelope can add issued_at and nonce and receives its own receipt_digest. V1 uses SHA-256 canonical digests for tamper evidence. Cryptographic signatures/key management are explicitly outside V1.

## Failure Policy
Missing required upstream receipts, mismatched identity bindings, invalid accumulated-loss claims, or protected execution without authorization fail closed. Unknown evidence/currentness remains representable rather than being coerced to success.

## Compatibility
Existing SQL_CONNECTOME_RECEIPT_V1 and existing Step 5-7 artifact digests remain valid. V1 adds a new cross-bound schema rather than silently changing old receipt semantics.