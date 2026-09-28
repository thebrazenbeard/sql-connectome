# PostgreSQL Translation Qualification V2

## Purpose

Translation qualification composes semantic translation evidence with a real PostgreSQL planning
result without collapsing those evidence states into behavioral equivalence.

The endpoint and MCP tool are unchanged. The response schema is now:

`SQL_CONNECTOME_TRANSLATION_QUALIFICATION_V2`

because the receipt contract materially strengthens what is cross-bound.

## Pipeline

```text
source SQL
  -> bounded source parse
  -> source semantic IR
  -> capability plan
  -> expression-semantic risk assessment
  -> explicit type-semantic projection
  -> generated PostgreSQL
  -> PostgreSQL target reparse / target semantic IR
  -> live PostgreSQL READ ONLY EXPLAIN
  -> qualification V2 receipt
```

## Fidelity evidence

Qualification V2 records independent fidelity components:

- `capability_fidelity`;
- `expression_semantic_fidelity`;
- `type_fidelity`;
- `translation_fidelity` as the combined ceiling.

Its exact scope label is:

`CAPABILITY_EXPRESSION_AND_TYPE_SEMANTICS`

Risk counts for expression and type semantics remain separate.

## Semantic cross-binding

The qualification binds:

- source SQL digest;
- generated target SQL digest;
- source semantic-IR digest;
- target semantic-IR digest;
- a canonical digest over the plan, expression semantics, type semantics, and combined fidelity.

The semantic-evidence digest makes the interpretation used for qualification independently
addressable rather than relying only on generated SQL text.

## Engine cross-binding

The qualification also binds:

- target runtime identity digest;
- engine-validation PASS/FAIL status;
- exact engine-validation receipt digest.

The engine receipt already binds the exact PostgreSQL runtime and target SQL digest. Qualification V2
therefore links source semantics -> generated target semantics -> exact engine-planning evidence.

## Claim ceiling

A PASS means:

- the translation pipeline produced PostgreSQL SQL under the reported fidelity ceiling; and
- the exact connected PostgreSQL runtime accepted and planned that generated SQL.

A PASS does **not** mean:

- the source and target produce equal rows for all inputs;
- the query was executed;
- performance is equivalent;
- write authority exists.

`TRANSLATE != ENGINE_VALIDATE != EXECUTE != BEHAVIORAL_EQUIVALENCE`
