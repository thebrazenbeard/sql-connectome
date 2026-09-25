---
name: sql-connectome
description: Use when a connected SQL Connectome MCP resource is available for SQL dialect analysis, translation, validation, schema inspection, or bounded read-only database work.
---

# SQL Connectome

Use SQL Connectome as an evidence-bearing SQL semantic and governed execution surface.

## Connection boundary

A plugin installation or this skill file does not prove that the SQL Connectome MCP resource is
connected. Before claiming a SQL Connectome operation occurred, require an actual tool result from
the connected MCP resource.

If the SQL Connectome tools are unavailable, say that the connection is unavailable rather than
inventing a result.

## Semantic boundary

Preserve this separation:

`UNDERSTAND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE`

- Dialect probing provides ranked evidence, not proof of identity.
- Translation fidelity is not behavioral equivalence.
- Target parser acceptance is not target-engine validation.
- PostgreSQL EXPLAIN validation is not query execution.
- DuckDB EXPLAIN validation is not query execution or cross-engine behavioral equivalence.
- SQLite EXPLAIN QUERY PLAN validation is not query execution or cross-engine behavioral equivalence.
- Read authority is not write authority.

Carry forward fidelity, semantic-loss, currentness, provenance, and authority fields returned by the
tools.

## Tool-selection guidance

- Use dialect probing when source dialect is uncertain.
- Parse before making semantic claims about unfamiliar SQL.
- Inspect expression contracts when function/operator/type semantics may differ across dialects.
- Use translation planning before transpiling when capability differences matter.
- Do not silently enable lossy translation.
- Use PostgreSQL validation when connected PostgreSQL engine/catalog acceptance matters without executing the query.
- Use DuckDB validation for embedded target-engine planning against caller-supplied schema context without external access.
- Use SQLite validation for embedded SQLite planner/catalog acceptance under query-only and compile-time authorization controls.
- Use bounded read-only execution only when the user needs actual result rows.
- Inspect schema/runtime state when a query depends on the connected database layout.

## Write boundary

The current SQL Connectome MCP surface intentionally has no protected write tool.

Do not simulate DDL, DML, migration, restore, role-management, or credential effects. A future write
surface must carry separate explicit authority and post-effect verification.
