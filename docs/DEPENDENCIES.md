# Dependency Boundaries

## SQLGlot

SQL Connectome uses SQLGlot as a parser/transpiler peripheral.

Current source pin:

`sqlglot>=30.19,<30.20`

Reasons for the narrow compatibility line:

- SQLGlot documents minor versions as potentially backwards-incompatible;
- SQL Connectome binds parser behavior to tests rather than silently accepting dependency drift;
- dialect parsing/transpilation remains replaceable behind the connectome semantic model.

SQLGlot is MIT licensed.

SQLGlot does **not** define SQL Connectome's truth model. In particular:

- parser acceptance is not target-engine validation;
- generated SQL is not proof of behavioral equivalence;
- SQLGlot warnings/errors do not grant execution authority;
- SQL Connectome capability, provenance, fidelity, validation, and governance state remain separate.

If SQLGlot is replaced or supplemented, the replacement must preserve these boundaries and pass the
same connectome contracts.
