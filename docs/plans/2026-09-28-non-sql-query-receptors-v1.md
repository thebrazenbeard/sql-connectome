# Non-SQL Query Receptors V1 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit PRQL, Cypher, SPARQL, and dataframe receptor mappings into the shared logical semantic graph.

**Architecture:** Define a provider-neutral receptor contract and language-specific capability maps. Receptors emit deterministic mapping evidence and only construct logical-plan subsets when every required construct is representable.

**Tech Stack:** Python 3.12, existing logical-plan and receipt digests, pytest, Ruff.

## Global Constraints
No foreign-language execution or authorization. No guessed mappings. Unsupported semantics remain explicit. Preserve source/version/provenance and semantic loss.

---

### Task 1: Receptor contract and mapping evidence
Create `src/sql_connectome/receptors.py`, tests. Define ReceptorLanguage, MappingState, ExternalPlan, ReceptorMapping and deterministic digest.

### Task 2: Language capability maps
Create `src/sql_connectome/receptor_capabilities.py`. Define explicit supported/unsupported construct maps for PRQL, Cypher, SPARQL, DATAFRAME and loss markers for known semantic gaps.

### Task 3: Logical-plan receptor
Create `src/sql_connectome/receptor_mapping.py`. Map normalized SCAN/FILTER/PROJECT/JOIN/AGGREGATE subset into existing LogicalPlan nodes; PARTIAL/UNSUPPORTED when source semantics exceed subset.

### Task 4: Receipt/conformance integration
Tests bind receptor mapping digest into Step 8 receipt evidence and preserve mapping loss into semantic-loss delta. Add deterministic cross-language cases without claiming source-language equivalence.

### Task 5: Hostile review and protected integration
Attack relationalization bias, graph-path loss, SPARQL bag/dataset/entailment assumptions, dataframe order/index/null assumptions, PRQL compiler-version drift, unsupported-construct guessing, and authority escalation. Run Ruff/full pytest and all protected exact-head checks before merge.

## Unresolved product decisions
None for V1. Native parsers/compilers for each external language and richer graph/RDF semantics remain later adapters built against this receptor contract.
