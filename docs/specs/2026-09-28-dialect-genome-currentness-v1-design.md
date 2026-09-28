# Dialect Genome Acquisition and Currentness V1

Status: APPROVED UNDER ROADMAP STANDING AUTHORIZATION

## Purpose
Represent what SQL Connectome knows about a dialect as versioned evidence, not as one mutable feature table.

## Architecture
A DialectGenome is a deterministic snapshot assembled from independent evidence observations. V1 defines three evidence classes: DEPENDENCY_METADATA, OFFICIAL_DOCUMENTATION, and ENGINE_PROBE. Observations bind dialect, feature/claim key, engine/version or source version where known, acquisition timestamp as evidence metadata, source locator/digest, observed value, and confidence/currentness state.

Reconciliation never overwrites disagreement. For each claim, a reconciliation artifact references all contributing observation digests and emits AGREES, CONFLICTS, INSUFFICIENT, or STALE with an explicit reason. Engine probes are behavioral evidence; documentation is documentary evidence; dependency metadata is implementation/currentness evidence. None is automatically promoted to universal semantic truth.

## Currentness
Currentness is version-relative. A genome records target dialect/version plus acquisition policy/version. Evidence can be CURRENT, STALE, UNKNOWN, or VERSION_MISMATCH. Timestamp alone cannot establish currentness. An observation for another engine version remains preserved but cannot silently qualify the target version.

## Acquisition
V1 provides provider-neutral ingestion APIs for externally acquired evidence and deterministic local probe-result ingestion. Network crawling, credentials, and paid services are outside core runtime. Official documentation locators and content digests are preserved so later acquisition jobs can refresh them independently.

## Integration
Genome and reconciliation digests can be attached as evidence refs to Step 8 receipts and Step 2 coercion/Step 3 validation evidence without changing those artifacts. Existing dialect behavior remains operational while genome evidence is introduced incrementally.

## Failure Policy
Conflicting evidence stays conflicting. Missing version/currentness stays explicit. Reconciliation cannot delete observations, invent source authority, or convert probe success into equivalence proof.
