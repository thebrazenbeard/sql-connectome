# Logical Semantic Plan V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

**Goal:** Add a deterministic typed bag-relational logical-plan layer above static SQL binding, with conservative schema, nullability, cardinality semantics and loss-accounted Substrait compatibility.

**Architecture:** Preserve SQLSemanticIR as source-shaped evidence and derive a separate immutable LogicalPlan from the qualified and typed binding expression. Logical relational nodes own output schemas and cardinality bounds; expressions use stable typed field and scope references. Substrait remains a compatibility boundary and cannot redefine internal semantics.

**Tech Stack:** Python 3.12, frozen dataclasses and enums, SQLGlot's already-qualified expression tree, canonical_digest, pytest, Ruff.

## Global Constraints

- Default relational multiplicity is BAG, never implicit set semantics.
- Preserve UNKNOWN for type, nullability, and cardinality facts that are not established.
- Stable field and scope IDs must not depend on Python object identity.
- Correlated references use explicit outer-scope identity, not AST depth.
- Logical plan construction must not mutate source or bound IR or elevate evidence authority.
- Cardinality is semantic bounds only; no optimizer or statistics estimates.
- Substrait compatibility is EXACT, EXTENSION_REQUIRED, UNREPRESENTABLE, or UNKNOWN and is not plan authority.
- Unsupported semantics remain explicit loss or unrepresentable evidence.
- V1 qualification does not claim SQL or engine behavioral equivalence.

---

### Task 1: Immutable logical-plan schema and deterministic serialization

**Files:** Create src/sql_connectome/connectome/logical_plan.py and tests/test_logical_plan.py; modify src/sql_connectome/connectome/__init__.py.

**Interfaces:** LogicalType, LogicalField, LogicalSchema, CardinalityBounds, LogicalExpression, LogicalRelation, LogicalPlan, logical_plan_digest(plan).

- [ ] Add failing tests for frozen model construction, duplicate node and field rejection, dangling input and reference rejection, bag default, UNKNOWN preservation, and deterministic digest.
- [ ] Run focused tests and record the missing-interface failure.
- [ ] Implement enums and dataclasses, validation, canonical as_dict(), and digest using canonical_digest. IDs are stable caller-supplied strings.
- [ ] Run focused tests and affected IR tests plus Ruff.
- [ ] Commit the independently passing deliverable as feat: add typed logical plan model.

### Task 2: Bound-SQL to logical-plan derivation

**Files:** Create src/sql_connectome/connectome/logical_builder.py and tests/test_logical_builder.py; modify binding.py and connectome/__init__.py.

**Interfaces:** build_logical_plan(typed, dialect_id, source_ir_digest, bound_ir_digest, schema_digest) -> LogicalPlan. bind_sql_text exposes a logical_semantics artifact.

- [ ] Add failing fixtures for READ to FILTER to PROJECT, stable alias identity, LIMIT cardinality, DISTINCT multiplicity, joins and outer-join null extension, aggregate cardinality, and unknown expression type.
- [ ] Implement deterministic post-binding traversal using structural path plus bound digest for stable IDs; propagate schemas, types, nullability and semantic bounds conservatively.
- [ ] Unsupported constructs emit explicit plan loss records rather than disappearing.
- [ ] Run focused binding and text-pipeline integration tests plus Ruff.
- [ ] Commit as feat: derive logical plans from bound sql.

### Task 3: Correlated scopes, set operations, and semantic invariants

Files: modify logical_builder.py and logical_plan.py; create tests/test_logical_scope_semantics.py.

Interfaces: explicit scope_id on relation scopes and outer_scope_id on correlated field references. Set-operation nodes require aligned output arity and preserve multiplicity mode.

- [ ] Add failing tests for correlated subquery capture, shadowed aliases, UNION ALL versus UNION, mismatched set-operation arity, aggregate without group, and outer-join null extension.
- [ ] Implement deterministic scope stack, explicit outer-reference resolution, set-operation schema alignment, and conservative cardinality and nullability propagation.
- [ ] Ambiguous or unresolved capture remains UNKNOWN or loss rather than guessed.
- [ ] Run logical-plan and binding tests plus Ruff.
- [ ] Commit as feat: add logical scope and set semantics.

### Task 4: Loss-accounted Substrait compatibility receptor

Files: create substrait_compat.py, tests/test_substrait_compat.py, docs/LOGICAL_SEMANTIC_PLAN.md; modify connectome/__init__.py.

Interface: inspect_substrait_compatibility(plan) returns per-feature EXACT, EXTENSION_REQUIRED, UNREPRESENTABLE, or UNKNOWN. V1 does not emit executable Substrait protobuf.

- [ ] Add failing tests for core relation and type mappings, correlated references, UNKNOWN types, dialect extensions, and unrepresentable states.
- [ ] Implement inspection-only mapping that preserves every non-exact reason and never mutates the plan.
- [ ] Run focused and full logical-plan tests plus Ruff.
- [ ] Commit as feat: add substrait compatibility inspection.

### Task 5: Qualification and integration

Files: create the exact-head hostile review record; update design status and progress ledger.

- [ ] Review set semantics, nullability, field IDs, correlated scopes, joins, aggregate cardinality, set operations, digest stability, and Substrait mapping. Add regression tests for accepted findings.
- [ ] Run an independent local-model review from D:/VERA when available and record model identity, artifact hash, reviewed head, prompt hash, findings, and protocol status.
- [ ] Run Ruff and full pytest. Feature failures block qualification.
- [ ] Push the exact head and require protected CI before merge.
- [ ] Merge only green exact heads and verify canonical main.

Unresolved externally observable decisions: none. Executable Substrait serialization and statistics-based cardinality estimates are outside V1.
