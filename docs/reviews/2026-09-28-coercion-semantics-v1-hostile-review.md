# Coercion Semantics V1 Hostile Review Record

**Design head reviewed:** `1c7d8e49f4f61d60b45157d27924eb774b074059`  
**Disposition head:** `e5fef409ca43205c1020f66cd651d0e20624e876`

## Internal hostile review

> **HOSTILE REVIEW:** The neutral vocabulary can still encode PostgreSQL assumptions indirectly. Require cross-engine falsification before qualification and preserve native observations losslessly.

Disposition: **accepted**. Cross-engine falsification and `UNMAPPED` behavior are design requirements.

> **HOSTILE REVIEW:** Source/target edges alone overstate value-, context-, version-, and session-dependent conversions.

Disposition: **accepted**. Context predicates, engine/version/session scope, structured effects, and contradictory evidence are part of claim identity and reconciliation.

> **HOSTILE REVIEW:** Unknown precision, collation, null, and temporal effects must not be inferred from canonical family.

Disposition: **accepted**. Unknown is the default for unbound effects.

## Independent local-model hostile review

**Runtime:** KoboldCpp 1.121, OpenAI/Kobold-compatible local server on Lappy  
**Model:** `D:\VERA\models\gguf\model_q5_k_s.gguf`  
**Model SHA-256:** `15150f534dc90ee15c82320ccc014463db7985205a7161228cff89b925fd1216`  
**Reported architecture:** Qwen3.5 4B, Q5_K_Medium  
**Prompt SHA-256:** `9638c2485a2c857ec91f8d3a335a04a93794b001db1a64459ca892a5768dd07a`

The full OpenAI-compatible review request failed at receive time, so it is not represented as a completed review. A reduced hostile probe through KoboldCpp's native generation endpoint completed and returned three objections:

> **INDEPENDENT HOSTILE REVIEW:** Context/version/session scoping risks fragmentation rather than a unified coercion view.

Disposition: **accepted as a design pressure, narrowed as a blocker**. The disposition head adds deterministic specificity-aware lookup. Narrow claims may override broad claims only by evidence-supported scope; equal-specificity conflicts return `CONTRADICTED`.

> **INDEPENDENT HOSTILE REVIEW:** Separating engine evidence from model synthesis limits adaptability.

Disposition: **rejected**. This separation is intentional. Model synthesis is review evidence and must not manufacture engine behavior.

> **INDEPENDENT HOSTILE REVIEW:** Preserving `UNKNOWN` can create unresolved/deadlocked coercion decisions.

Disposition: **accepted**. The disposition head requires deterministic `UNKNOWN`/`CONTRADICTED` returns and makes effect policy an explicit caller decision rather than an invented semantic fallback.

## Review state

**Internal hostile review:** completed.  
**Independent model review:** completed at reduced-probe strength; full-protocol attempt failed and remains recorded as such.  
**Result:** **SURVIVES_NARROWED**.

The design was narrowed to specify deterministic claim selection and explicit unknown/conflict handling before implementation planning.
