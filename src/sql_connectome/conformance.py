from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .engine_validation import EngineRuntimeIdentity, NativeEngineError
from .receipts import canonical_digest


class ComparisonMode(StrEnum):
    ORDERED = "ORDERED"
    BAG = "BAG"
    SET = "SET"
    ERROR_CLASS = "ERROR_CLASS"


class ComparisonState(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ComparisonPolicy:
    mode: ComparisonMode
    allow_nondeterminism: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"mode": self.mode.value, "allow_nondeterminism": self.allow_nondeterminism}


@dataclass(frozen=True, slots=True)
class ConformanceCase:
    case_id: str
    seed: int
    setup_sql: tuple[str, ...]
    source_sql: str
    transformed_sql: str
    comparison_policy: ComparisonPolicy
    invariant: bool = False
    assumptions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_CONFORMANCE_CASE_V1",
            "case_id": self.case_id,
            "seed": self.seed,
            "setup_sql": list(self.setup_sql),
            "source_sql": self.source_sql,
            "transformed_sql": self.transformed_sql,
            "comparison_policy": self.comparison_policy.as_dict(),
            "invariant": self.invariant,
            "assumptions": list(self.assumptions),
        }


@dataclass(frozen=True, slots=True)
class ExecutionObservation:
    runtime: EngineRuntimeIdentity
    case_digest: str
    sql_digest: str
    rows: tuple[tuple[Any, ...], ...] | None = None
    native_error: NativeEngineError | None = None
    session_facts: tuple[tuple[str, str], ...] = ()
    available: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_EXECUTION_OBSERVATION_V1",
            "runtime": self.runtime.as_dict(),
            "case_digest": self.case_digest,
            "sql_digest": self.sql_digest,
            "rows": [list(row) for row in self.rows] if self.rows is not None else None,
            "native_error": self.native_error.as_dict() if self.native_error else None,
            "session_facts": dict(sorted(self.session_facts)),
            "available": self.available,
        }


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    state: ComparisonState
    left_digest: str
    right_digest: str
    policy: ComparisonPolicy
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_COMPARISON_RESULT_V1",
            "state": self.state.value,
            "left_digest": self.left_digest,
            "right_digest": self.right_digest,
            "policy": self.policy.as_dict(),
            "reason": self.reason,
        }


def conformance_case_digest(case: ConformanceCase) -> str:
    return canonical_digest(case.as_dict())


def execution_observation_digest(observation: ExecutionObservation) -> str:
    return canonical_digest(observation.as_dict())


def comparison_result_digest(result: ComparisonResult) -> str:
    return canonical_digest(result.as_dict())


def _comparable(value: Any) -> str:
    return canonical_digest({"value": value})


def compare_observations(
    left: ExecutionObservation,
    right: ExecutionObservation,
    policy: ComparisonPolicy,
) -> ComparisonResult:
    left_digest = execution_observation_digest(left)
    right_digest = execution_observation_digest(right)
    if not left.available or not right.available:
        return ComparisonResult(
            ComparisonState.UNAVAILABLE, left_digest, right_digest, policy, "execution unavailable"
        )
    if policy.allow_nondeterminism:
        return ComparisonResult(
            ComparisonState.INCONCLUSIVE,
            left_digest,
            right_digest,
            policy,
            "nondeterministic comparison not qualified",
        )
    if policy.mode is ComparisonMode.ERROR_CLASS:
        if left.native_error is None or right.native_error is None:
            state = ComparisonState.INCONCLUSIVE
            reason = "both observations must contain native errors"
        else:
            state = (
                ComparisonState.MATCH
                if left.native_error.error_class == right.native_error.error_class
                else ComparisonState.MISMATCH
            )
            reason = "native error class comparison"
        return ComparisonResult(state, left_digest, right_digest, policy, reason)
    if left.native_error is not None or right.native_error is not None:
        return ComparisonResult(
            ComparisonState.MISMATCH,
            left_digest,
            right_digest,
            policy,
            "unexpected execution error",
        )
    if left.rows is None or right.rows is None:
        return ComparisonResult(
            ComparisonState.INCONCLUSIVE,
            left_digest,
            right_digest,
            policy,
            "row evidence missing",
        )
    if policy.mode is ComparisonMode.ORDERED:
        matched = left.rows == right.rows
    elif policy.mode is ComparisonMode.BAG:
        matched = Counter(map(_comparable, left.rows)) == Counter(map(_comparable, right.rows))
    elif policy.mode is ComparisonMode.SET:
        matched = set(map(_comparable, left.rows)) == set(map(_comparable, right.rows))
    else:
        return ComparisonResult(
            ComparisonState.INCONCLUSIVE,
            left_digest,
            right_digest,
            policy,
            "unsupported comparison policy",
        )
    return ComparisonResult(
        ComparisonState.MATCH if matched else ComparisonState.MISMATCH,
        left_digest,
        right_digest,
        policy,
        "rows compared without value coercion",
    )
