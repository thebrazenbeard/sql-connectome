# Contributing

SQL Connectome accepts changes that increase dialect coverage, semantic precision, validation
strength, or execution safety without collapsing distinct evidence states.

## Core rule

Keep these states separate:

`PARSE != BIND != TRANSLATE != TARGET_PARSE != ENGINE_VALIDATE != EXECUTE != AUTHORIZE`

A change must not use a weaker state as evidence for a stronger one.

## Dialect and semantic claims

Prefer evidence in this order:

1. official engine documentation or standards text;
2. reproducible behavior from the exact engine/version;
3. pinned parser/transpiler metadata used as explicit dependency evidence;
4. clearly labeled inference.

When source and target behavior differs only under a condition, record the condition instead of
claiming universal divergence.

## Development

Use Python 3.12.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
ruff check .
pytest -q
```

Database integration tests use PostgreSQL 17. Apply migrations twice when modifying migration
behavior to verify replay/idempotency.

## Pull requests

Use the repository pull request template. Keep changes narrowly scoped, include tests for every
new semantic claim, and preserve explicit fidelity/authority ceilings.

Security vulnerabilities must follow `SECURITY.md` rather than being disclosed in a public issue.
