# Evidence-Bearing Coercion Semantics

SQL Connectome coercion semantics V1 separates engine observations from reconciled semantic claims.

The legacy `SQL_CONNECTOME_TYPE_GRAPH_V1` remains dependency-derived topology. Its missing edges continue to mean `UNKNOWN_NOT_UNSUPPORTED`. V2 evidence records preserve source/target direction, engine/dialect/version/context/session scope, native metadata, provenance, evidence basis, qualification state, and structured semantic effects.

Reconciliation is deterministic over an explicit evidence set. Exact evidenced scope is more specific than broad scope; equally specific incompatible qualified observations produce `CONTRADICTED`; absence of a qualified match produces `UNKNOWN`. Neither state silently authorizes execution.

PostgreSQL `pg_cast` is admitted as engine-catalog evidence. Native `castcontext` and `castmethod` values remain preserved verbatim. Catalog evidence is not treated as proof of global behavioral equivalence, and catalog absence is not treated as unsupported behavior.

Model hostile reviews are review evidence only. They can narrow or block an architectural claim but cannot promote documentation, dependency metadata, or catalog observations into behavioral engine evidence.

Current behavioral ceiling: `NOT_ESTABLISHED`. Real-engine probes and independent currentness acquisition belong to later ordered program work.
