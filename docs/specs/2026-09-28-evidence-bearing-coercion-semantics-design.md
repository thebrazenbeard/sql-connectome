# Evidence-Bearing Coercion Semantics V1 — Design

**Status:** proposed for hostile review  
**Canonical base:** `fb19dd0a1c84cb89466bea7a48e7a364799bbe79`  
**Scope:** ordered program step 2 only

## Decision

SQL Connectome will model coercion through a provider-neutral semantic claim layer. Engine-native cast categories remain lossless observations attached as evidence; they do not define the universal ontology.

The existing SQLGlot `COERCES_TO` graph remains a dependency-derived observation. It becomes one input to reconciliation, not authoritative engine behavior. Existing missing-edge semantics remain `UNKNOWN_NOT_UNSUPPORTED`.

## Invariants

- Direction is explicit: source type -> target type. Reverse behavior requires a separate claim.
- Evidence is append-only by identity; reconciliation never erases contradictory observations.
- `UNKNOWN`, `UNMAPPED`, `CONTRADICTED`, and `NOT_APPLICABLE` are representable without coercing them into yes/no support.
- Evidence class and qualification state are orthogonal. LLM review cannot promote documentation or dependency evidence to behavioral evidence.
- Engine identity, engine version/range, dialect identity, dependency version, and session assumptions are part of claim scope.
- Precision/scale, nullability, collation, character set, and time-zone effects are structured effects, not booleans.

## Provider-neutral semantic claim

A reconciled coercion claim identifies source and target canonical/dialect types plus a context predicate. Context is extensible and initially admits: explicit cast, assignment/storage, comparison, arithmetic, function/operator argument, set operation, CASE/result mixing, COALESCE/result mixing, literal resolution, parameter binding, and generic expression resolution.

Permission is represented independently from native labels: `ALLOWED`, `REJECTED`, `CONDITIONAL`, or `UNKNOWN`. Invocation is `EXPLICIT_ONLY`, `IMPLICIT`, `ENGINE_SELECTED`, or `UNKNOWN`; native modes such as PostgreSQL `i/a/e` are retained verbatim in evidence metadata.

Each claim carries structured effects for numeric precision/scale/range, null behavior, character set/collation, temporal/time-zone behavior, representation method, and session dependencies. Unobserved fields remain unknown. No inference from canonical family alone may silently populate engine behavior.

## Evidence record

An evidence record is immutable and digestible. It contains an evidence ID, engine/dialect/version scope, source/target type identity, context, observed native category/method, structured effects actually supported by the source, source basis, locator/provenance, capture/currentness metadata, qualification state, and optional counterexample/negative evidence.

Initial source-basis classes are `DEPENDENCY_METADATA`, `OFFICIAL_DOCUMENTATION`, `ENGINE_CATALOG`, `ENGINE_PROBE`, `FORMAL_SPECIFICATION`, and `DERIVED_INFERENCE`. Model reviews use a separate `REVIEW` record class and never become coercion evidence.

## Qualification and reconciliation

Qualification states are `PROPOSED`, `SOURCE_BOUND`, `HOSTILE_REVIEWED`, `BEHAVIORALLY_PROBED`, `CONTRADICTED`, `STALE`, and `QUALIFIED`. Qualification is claim-specific; a source can support one field while leaving another unknown.

Reconciliation is deterministic over an explicit evidence set. It emits the evidence-set digest, reconciler/schema version, resulting claim, unresolved conflicts, evidence ceiling, and currentness status. Stronger evidence does not delete weaker evidence. Conflicting engine probes prevent `QUALIFIED` unless the conflict is scoped by version/session/context or explicitly remains unresolved.

Claim lookup is deterministic and specificity-aware. Exact engine version/session/context predicates outrank broader predicates only when both are evidence-supported; broader claims never overwrite narrower contradictory claims. If multiple equally specific qualified claims conflict, lookup returns `CONTRADICTED` rather than choosing one. If no qualified claim matches, lookup returns `UNKNOWN`. Callers must explicitly choose whether unknown/contradicted results block an effect, request more evidence, or remain descriptive; the semantic layer itself never invents a fallback.

The public V2 type graph is a projection of reconciled claims plus raw dependency observations. V1 remains readable during migration. Consumers must be able to distinguish raw observation, reconciled claim, and derived topology.

## Hostile-review protocol

Every major semantic design/revision receives:
1. internal hostile review;
2. at least one independently executed model review when a usable independent runtime exists;
3. exact artifact digest and Git head binding;
4. reviewer/model/runtime identity and lineage;
5. prompt/protocol digest;
6. findings with severity and concrete counterexample where possible;
7. disposition: accepted, narrowed, rejected-with-reason, unresolved, or stale.

Internal hostile review is never independent review. Multiple model agreements are review corroboration, not database-behavior evidence.

> **HOSTILE REVIEW:** A provider-neutral ontology can become PostgreSQL-shaped by vocabulary rather than by explicit dependency. Every neutral field must survive comparison against materially different engines. Native facts must remain lossless, and foreign behavior must be allowed to remain unmapped.
>
> **HOSTILE REVIEW:** A single edge is probably insufficient for value-dependent and session-dependent conversions. The claim identity must include context and predicates, or the graph will state false universals.
>
> **HOSTILE REVIEW:** Precision, collation, and time-zone effects cannot be inferred safely from source/target type names. Unknown must be the default until evidence binds the effect.

## PostgreSQL seed mapping

PostgreSQL `pg_cast` is an engine-catalog evidence source, not a complete cast universe. `castcontext` and `castmethod` are preserved verbatim. Generic conversions not represented in `pg_cast` remain separately sourced. Documentation and catalog/probe evidence are distinct records.

The initial mapping may translate PostgreSQL native context into candidate neutral claims only when the mapping is lossless for that claim. Otherwise the native observation remains `UNMAPPED`.

## Cross-engine falsification cases

Before V1 qualification, the ontology must represent without distortion:
- PostgreSQL expression/assignment/explicit cast distinctions and function/I-O/binary methods;
- MySQL expression and assignment conversions whose results depend on operand/context or SQL/session modes;
- MariaDB comparison/arithmetic rules, including version-sensitive behavior;
- temporal conversion with range/information loss;
- collation/character-set derivation and conflict;
- a conversion rejected in one context but admitted in another.

These are ontology falsification tests, not claims that engines are equivalent.

## Migration boundary

`dialect_type_graph()` remains callable. A V2 implementation introduces evidence records and reconciliation behind a versioned schema. Existing V1 tests continue to pass until a deliberate compatibility retirement. No consumer is silently upgraded from dependency topology to engine-qualified semantics.

## Non-goals

This step does not add MySQL/MariaDB execution adapters, a logical relational plan, rewrite hyperedges, ADBC, or the full dialect-genome acquisition service. It defines the semantic/evidence substrate those later ordered steps consume.

## Acceptance

The design is ready for implementation planning only after hostile review findings are dispositioned, an independent-model review is attempted and recorded, and the schema can encode the cross-engine falsification cases without treating PostgreSQL terminology as universal truth. Unknown and contradictory lookup behavior must be deterministic and non-deadlocking.
