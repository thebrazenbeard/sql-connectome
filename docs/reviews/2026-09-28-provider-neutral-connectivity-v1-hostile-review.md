# Provider-Neutral Connectivity V1 — Internal Hostile Review

Reviewed head lineage through `9232994122269243e23c67fe28e7988cdc2e1528`.

Attacks: secret leakage, transport-as-semantic-authority, protected-effect authorization confusion, catalog/session identity drift, SQL-classifier overclaim, native error laundering, and ADBC hard dependency.

Disposition: SURVIVES_NARROWED.

The adapter never infers effect class from SQL. Callers must supply it, and all non-read-only/unknown effects require an external authorization receipt. This avoids a connectivity-layer parser becoming an authority oracle. Identity serialization has no credential fields. ADBC is optional and factory-injected. Native errors remain in execution evidence.

Limitation: V1 trusts adapter-supplied catalog/session facts at session creation; active re-attestation after in-session catalog/session mutation is not yet implemented. Therefore V1 must not claim session-currentness after arbitrary session-changing SQL. Step 8 receipts must carry this uncertainty and Step 9 currentness work should address re-attestation.

Independent-model review: NOT PERFORMED. Internal hostile review only.
