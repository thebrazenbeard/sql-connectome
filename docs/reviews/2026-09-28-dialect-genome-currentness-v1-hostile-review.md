# Dialect Genome and Currentness V1 — Internal Hostile Review

Reviewed implementation lineage through `7567da02f2d68cdea0b0803cfe7528f695b4fedc`.

## Attacks
1. Authority laundering: DEPENDENCY_METADATA, OFFICIAL_DOCUMENTATION, and ENGINE_PROBE remain distinct evidence classes; agreement is corroboration, not truth.
2. Conflict erasure: reconciliation preserves every contributing observation digest and emits CONFLICTS when usable observations disagree.
3. Version aliasing: source/engine versions and genome target version are independently bound; VERSION_MISMATCH remains explicit.
4. Timestamp-currentness confusion: acquired_at is evidence metadata only; currentness is an explicit state.
5. Stale-evidence promotion: all stale/version-mismatched inputs reconcile to STALE rather than AGREES.
6. Source substitution: locator and source digest are both bound into each observation digest.
7. Cross-dialect contamination: DialectGenome rejects observations for another dialect.
8. Probe overclaim: probe observations record behavior only and do not imply semantic equivalence.
9. Network/credential coupling: acquisition constructors ingest evidence; they perform no fetching and require no credentials.

## Finding
SURVIVES_NARROWED.

V1 is an evidence/currentness substrate, not yet a vendor-specific automated crawler or exhaustive probe catalog. That limitation is explicit.

Independent-model review: NOT PERFORMED. This is internal hostile review only.
