from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .conformance import (
    ComparisonResult,
    ComparisonState,
    ConformanceCase,
    compare_observations,
    conformance_case_digest,
)
from .conformance_runners import ConformanceRunner
from .receipts import canonical_digest


@dataclass(frozen=True, slots=True)
class RewriteQualificationReport:
    rewrite_id: str
    rewrite_version: str
    rewrite_application_digest: str
    case_digest: str
    engine_results: tuple[tuple[str, str, str], ...]
    qualification: str
    counterexamples: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_REWRITE_QUALIFICATION_V1",
            "rewrite_id": self.rewrite_id,
            "rewrite_version": self.rewrite_version,
            "rewrite_application_digest": self.rewrite_application_digest,
            "case_digest": self.case_digest,
            "engine_results": [list(item) for item in self.engine_results],
            "qualification": self.qualification,
            "counterexamples": list(self.counterexamples),
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


def qualify_rewrite(
    *,
    rewrite_id: str,
    rewrite_version: str,
    rewrite_application_digest: str,
    case: ConformanceCase,
    runners: tuple[ConformanceRunner, ...],
) -> RewriteQualificationReport:
    results: list[tuple[str, str, str]] = []
    counterexamples: list[str] = []
    all_match = True
    for runner in runners:
        source = runner.execute(case, case.source_sql)
        transformed = runner.execute(case, case.transformed_sql)
        comparison: ComparisonResult = compare_observations(
            source, transformed, case.comparison_policy
        )
        results.append((runner.runtime.engine, comparison.state.value, comparison.reason))
        if comparison.state is not ComparisonState.MATCH:
            all_match = False
            counterexamples.append(
                f"{runner.runtime.engine}:{comparison.state.value}:"
                f"{comparison.left_digest}:{comparison.right_digest}"
            )
    return RewriteQualificationReport(
        rewrite_id=rewrite_id,
        rewrite_version=rewrite_version,
        rewrite_application_digest=rewrite_application_digest,
        case_digest=conformance_case_digest(case),
        engine_results=tuple(results),
        qualification="BEHAVIORALLY_QUALIFIED_CASE_BOUND" if all_match else "NOT_QUALIFIED",
        counterexamples=tuple(counterexamples),
    )
