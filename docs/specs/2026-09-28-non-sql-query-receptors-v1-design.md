# Non-SQL Query Receptors V1

Status: APPROVED UNDER ROADMAP STANDING AUTHORIZATION

## Purpose
Expose PRQL, Cypher, SPARQL, and dataframe plans through explicit, loss-accounted mappings into supported subsets of the existing logical semantic graph.

## Architecture
A receptor does not parse or execute a foreign language. It accepts a normalized external-plan description plus source provenance and maps supported constructs to Connectome logical relation/expression kinds. Every mapping result records receptor/language/version, supported and unsupported constructs, semantic-loss markers, source digest, output logical-plan digest when available, and qualification state.

V1 defines capability maps for PRQL relational pipelines, Cypher graph pattern/projection/filter subsets, SPARQL basic graph pattern/filter/project subsets, and dataframe scan/filter/project/join/aggregate subsets. Graph-specific path semantics, SPARQL entailment/dataset semantics, PRQL compiler-specific extensions, and dataframe index/order/null idiosyncrasies remain explicit unsupported/loss boundaries.

## Safety and Authority
Receptors are semantic ingress only. They cannot validate against an engine, execute, authorize effects, or claim equivalence. Their receipts can feed Step 8 UNDERSTAND/BIND transitions and Step 6 conformance evidence.

## Failure Policy
Unsupported constructs produce PARTIAL or UNSUPPORTED mappings, never guessed SQL. Unknown constructs are retained as evidence and block FULL qualification.
