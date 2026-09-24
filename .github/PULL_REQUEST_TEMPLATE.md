## Exact subject

- Base branch:
- Head SHA:
- Source dialect(s):
- Target dialect(s):
- Engine/runtime subject, if any:

## Change

Describe the smallest coherent change and the SQL Connectome layer it affects.

## Claim ceiling

Check every statement that applies.

- [ ] Parser acceptance is not being presented as engine validation.
- [ ] Translation is not being presented as behavioral equivalence.
- [ ] Engine planning is not being presented as query execution.
- [ ] Execution authority has not been inferred from routing or semantic understanding.
- [ ] Any LOSSY or UNREPRESENTABLE behavior is explicit.
- [ ] Dependency-derived semantic claims identify their evidence/version.

## Verification

- [ ] `ruff check .`
- [ ] `pytest -q`
- [ ] Migration replay/idempotency checked when migrations changed.
- [ ] Relevant source/target parser tests added or updated.
- [ ] Relevant real-engine validation added or updated when an engine claim changed.
- [ ] Security boundary reviewed when parsing, execution, credentials, filesystem, network, or extensions changed.

## Provenance

List official dialect/engine documentation, standards references, upstream dependency evidence, and
exact runtime evidence used to support new semantic claims.

## Protected effects

List any deployment, credential, provider, migration, release, or other protected effect requested
by this PR. Write `none` when the PR is source-only.
