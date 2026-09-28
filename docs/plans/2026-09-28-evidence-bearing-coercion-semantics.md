# Evidence-Bearing Coercion Semantics V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add versioned, evidence-bearing, provider-neutral coercion semantics while preserving the existing dependency-derived V1 type graph unchanged.

**Architecture:** Introduce immutable evidence, claim, effect, and reconciliation types beside the current `type_system.py` V1 topology. Deterministic reconciliation will consume explicit evidence sets, preserve native engine observations and conflicts, and expose qualified/unknown/contradicted claims without inventing behavioral support. PostgreSQL seed mapping will prove the neutral substrate can preserve `pg_cast` categories without making them universal.

**Tech Stack:** Python 3.12, dataclasses, StrEnum, existing `canonical_digest`, pytest, Ruff.

## Global Constraints

- Provider-neutral semantic claims are authoritative; engine-native cast categories remain lossless evidence.
- Direction, context, engine/version/session scope, and predicates are explicit.
- Precision/scale/range, null, charset/collation, temporal/time-zone, representation, and session effects default to unknown until evidence binds them.
- Evidence basis and qualification state remain orthogonal; review records never become coercion evidence.
- Reconciliation is deterministic over an explicit evidence set and preserves contradictions.
- Exact evidenced scope outranks broader scope; equal-specificity conflicts return `CONTRADICTED`; no qualified match returns `UNKNOWN`.
- Existing `SQL_CONNECTOME_TYPE_GRAPH_V1`, `dialect_type_graph()`, `type_graph_digest()`, and missing-edge meaning remain backward compatible.
- No MySQL/MariaDB execution adapter, logical relational plan, rewrite hyperedge, ADBC layer, or dialect-genome acquisition service is added in this step.

---

### Task 1: Immutable neutral coercion schema and canonical serialization

**Files:**
- Create: `src/sql_connectome/connectome/coercion_semantics.py`
- Modify: `src/sql_connectome/connectome/__init__.py`
- Test: `tests/test_coercion_semantics.py`

**Interfaces:**
- Consumes: `CanonicalTypeFamily`, `canonical_digest(payload)`.
- Produces: `CoercionContext`, `CoercionPermission`, `CoercionInvocation`, `EvidenceBasis`, `QualificationState`, `EffectState`, `TypeIdentity`, `CoercionScope`, `CoercionEffects`, `CoercionEvidence`, `CoercionClaim`, and deterministic `as_dict()`/digest behavior.

- [ ] **Step 1: Add the focused failing test**

Assert enum values are provider-neutral; source/target direction is retained; native categories are opaque metadata; all structured effect dimensions serialize as `UNKNOWN` by default; evidence identity includes engine/dialect/version/context/session scope; and equivalent objects produce identical canonical digests.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_coercion_semantics.py`  
Expected: collection/import failure because the V2 coercion interfaces do not exist.

- [ ] **Step 3: Implement the minimum behavior**

Use frozen slot dataclasses. Keep engine-native mode/method as immutable key/value metadata rather than adding PostgreSQL-specific enum members. Represent version scope with explicit optional minimum/maximum/exact strings without interpreting vendor version ordering in this task. Represent context predicates and session assumptions as sorted immutable key/value tuples. Structured effects expose explicit unknown state and optional evidenced detail; no canonical-family inference populates them.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_coercion_semantics.py`  
Expected: Task 1 schema/serialization tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m pytest -q tests/test_type_system.py tests/test_coercion_semantics.py && py -m ruff check src/sql_connectome/connectome/coercion_semantics.py src/sql_connectome/connectome/__init__.py tests/test_coercion_semantics.py`  
Expected: V1 type-system tests and new schema tests pass; Ruff reports no errors.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/connectome/coercion_semantics.py src/sql_connectome/connectome/__init__.py tests/test_coercion_semantics.py
git commit -m "feat: add neutral coercion evidence schema"
```

### Task 2: Deterministic evidence reconciliation and lookup

**Files:**
- Modify: `src/sql_connectome/connectome/coercion_semantics.py`
- Test: `tests/test_coercion_semantics.py`

**Interfaces:**
- Consumes: immutable `CoercionEvidence` records from Task 1.
- Produces: `ReconciliationResult`, `ClaimLookupResult`, `reconcile_coercion_evidence(evidence)`, and `lookup_coercion_claim(results, scope)`.

- [ ] **Step 1: Add the focused failing test**

Cover: input-order-independent reconciliation/digest; identical supported observations coalesce without deleting provenance; narrower exact version/session/context scope wins only when matched; equally specific incompatible qualified evidence yields `CONTRADICTED`; no qualified match yields `UNKNOWN`; weaker evidence remains visible; review-only records are rejected from the coercion-evidence input type rather than counted as engine evidence.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_coercion_semantics.py -k "reconcile or lookup or conflict"`  
Expected: failures because reconciliation/lookup interfaces are absent.

- [ ] **Step 3: Implement the minimum behavior**

Canonical-sort evidence by stable evidence ID/digest before reconciliation. Group only records with compatible semantic identity and scope. Emit evidence-set digest, schema/reconciler version, evidence ceiling, claim, contributing evidence IDs, and unresolved conflicts. Specificity is computed only from explicit scope fields; no guessed version precedence. Lookup returns a state object rather than raising for semantic unknown/conflict.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_coercion_semantics.py -k "reconcile or lookup or conflict"`  
Expected: deterministic reconciliation/lookup cases pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m pytest -q tests/test_coercion_semantics.py tests/test_type_system.py`  
Expected: all coercion and legacy type tests pass.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/connectome/coercion_semantics.py tests/test_coercion_semantics.py
git commit -m "feat: reconcile scoped coercion evidence"
```

### Task 3: Preserve V1 dependency topology as V2 evidence projection

**Files:**
- Modify: `src/sql_connectome/connectome/type_system.py`
- Modify: `src/sql_connectome/connectome/text_pipeline.py`
- Modify: `src/sql_connectome/connectome/__init__.py`
- Test: `tests/test_type_system.py`
- Test: `tests/test_coercion_semantics.py`

**Interfaces:**
- Consumes: existing `Dialect.COERCES_TO`, `dialect_type_graph()`, V2 evidence schema.
- Produces: `dependency_coercion_evidence(dialect_id, parser_dialect)` and a versioned inspection path exposing raw V1 topology separately from V2 evidence/reconciliation.

- [ ] **Step 1: Add the focused failing test**

Assert every projected SQLGlot edge is `DEPENDENCY_METADATA`, carries the dependency version and `COERCION_SHAPE_ONLY` ceiling, never claims behavioral qualification, preserves `UNKNOWN_NOT_UNSUPPORTED`, and leaves the exact existing V1 graph/digest unchanged. Assert V2 inspection distinguishes raw evidence from reconciled claims.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_type_system.py tests/test_coercion_semantics.py -k "dependency or graph or inspect"`  
Expected: V2 projection assertions fail because only V1 graph output exists.

- [ ] **Step 3: Implement the minimum behavior**

Map each SQLGlot edge to a directional evidence record with native source locator `SQLGLOT_COERCES_TO`, dependency version, generic-expression context only where the dependency metadata actually supports that shape, unknown structured effects, and non-behavioral qualification. Do not rewrite `dialect_type_graph()`; build the V2 projection from it or the same source without changing V1 serialization.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_type_system.py tests/test_coercion_semantics.py -k "dependency or graph or inspect"`  
Expected: V1 compatibility and V2 dependency-evidence tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m pytest -q tests/test_type_system.py tests/test_text_pipeline.py tests/test_coercion_semantics.py`  
Expected: legacy inspection/transpilation behavior remains passing and V2 inspection is additive.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/connectome/type_system.py src/sql_connectome/connectome/text_pipeline.py src/sql_connectome/connectome/__init__.py tests/test_type_system.py tests/test_coercion_semantics.py
git commit -m "feat: project dependency coercions as evidence"
```

### Task 4: PostgreSQL native evidence seed and cross-engine falsification fixtures

**Files:**
- Create: `src/sql_connectome/connectome/coercion_sources.py`
- Modify: `src/sql_connectome/connectome/__init__.py`
- Test: `tests/test_coercion_sources.py`
- Test: `tests/test_coercion_semantics.py`

**Interfaces:**
- Consumes: neutral evidence schema; explicit PostgreSQL catalog rows supplied by callers/fixtures.
- Produces: `postgresql_pg_cast_evidence(rows, engine_version, provenance)` plus neutral falsification fixtures used only for ontology tests.

- [ ] **Step 1: Add the focused failing test**

Supply representative `pg_cast` rows and assert native `castcontext` values `i/a/e` and `castmethod` values `f/i/b` survive verbatim; neutral mapping is emitted only for lossless context facts; catalog absence is never interpreted as unsupported. Add synthetic MySQL/MariaDB-shaped evidence fixtures proving the schema can represent session-dependent assignment, version-sensitive comparison, collation conflict, temporal information loss, and context-specific rejection without adding engine-specific neutral enums.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_coercion_sources.py tests/test_coercion_semantics.py -k "postgres or mysql or mariadb or falsification"`  
Expected: import/assertion failures because source adapters/fixtures are absent.

- [ ] **Step 3: Implement the minimum behavior**

The PostgreSQL source adapter accepts already-retrieved catalog rows; it does not open database connections in this step. Preserve native values in evidence metadata, bind engine/version/provenance, and map `i/a/e` only to neutral invocation/context statements that are explicitly justified. Keep `f/i/b` as representation evidence rather than universal conversion modes. Cross-engine fixtures are tests of representational adequacy, not behavioral truth claims.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_coercion_sources.py tests/test_coercion_semantics.py -k "postgres or mysql or mariadb or falsification"`  
Expected: all source-mapping and ontology-falsification tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m pytest -q tests/test_coercion_sources.py tests/test_coercion_semantics.py tests/test_type_system.py`  
Expected: source mapping, reconciliation, falsification, and V1 compatibility all pass.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/connectome/coercion_sources.py src/sql_connectome/connectome/__init__.py tests/test_coercion_sources.py tests/test_coercion_semantics.py
git commit -m "feat: add PostgreSQL coercion evidence source"
```

### Task 5: Qualification manifest, documentation, and full regression gate

**Files:**
- Modify: `docs/specs/2026-09-28-evidence-bearing-coercion-semantics-design.md`
- Create: `docs/COERCION_SEMANTICS.md`
- Test: `tests/test_coercion_semantics.py`

**Interfaces:**
- Consumes: all V2 public interfaces and hostile-review record.
- Produces: documented schema/qualification ceiling and a machine-readable `coercion_semantics_manifest()` binding schema version, reconciler version, dependency version, evidence-set digest, and behavioral ceiling.

- [ ] **Step 1: Add the focused failing test**

Assert the manifest is deterministic, names the V2 schema/reconciler versions, exposes evidence/currentness ceilings without claiming behavioral equivalence, and changes digest when its explicit evidence set changes.

- [ ] **Step 2: Verify the relevant failure**

Run: `py -m pytest -q tests/test_coercion_semantics.py -k manifest`  
Expected: failure because the manifest interface is absent.

- [ ] **Step 3: Implement the minimum behavior**

Add the manifest and document evidence classes, qualification states, lookup semantics, PostgreSQL seed ceiling, V1 compatibility, hostile-review provenance, and explicit non-goals. Mark V2 as evidence-bearing but not globally behaviorally qualified until real-engine probes exist.

- [ ] **Step 4: Verify the focused pass**

Run: `py -m pytest -q tests/test_coercion_semantics.py -k manifest`  
Expected: manifest tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `py -m ruff check . && py -m pytest -q`  
Expected: Ruff clean and the complete repository test suite passes. Record exact counts and exact implementation head before any completion/merge claim.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add src/sql_connectome/connectome/coercion_semantics.py docs/specs/2026-09-28-evidence-bearing-coercion-semantics-design.md docs/COERCION_SEMANTICS.md tests/test_coercion_semantics.py
git commit -m "docs: qualify evidence-bearing coercion semantics"
```

## Unresolved Product Decisions

None required to begin implementation. Vendor version ordering is intentionally not generalized in V1; callers provide exact/range scope strings and later dialect-genome work can introduce engine-specific version comparators without changing evidence identity.
