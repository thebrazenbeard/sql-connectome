from sql_connectome.conformance import (
    ComparisonMode,
    ComparisonPolicy,
    ComparisonState,
    ConformanceCase,
    ExecutionObservation,
    compare_observations,
    conformance_case_digest,
    execution_observation_digest,
)
from sql_connectome.engine_validation import EngineRuntimeIdentity


def _case() -> ConformanceCase:
    return ConformanceCase(
        case_id="case-1",
        seed=7,
        setup_sql=("CREATE TABLE t(a INTEGER)", "INSERT INTO t VALUES (1), (2), (2)"),
        source_sql="SELECT a FROM t",
        transformed_sql="SELECT a FROM t",
        comparison_policy=ComparisonPolicy(ComparisonMode.BAG),
        invariant=True,
    )


def test_case_digest_is_deterministic() -> None:
    case = _case()
    assert conformance_case_digest(case) == conformance_case_digest(case)


def test_observation_digest_binds_runtime_and_session() -> None:
    case = _case()
    first = ExecutionObservation(
        runtime=EngineRuntimeIdentity("sqlite", "sqlite-conformance-v1", "3"),
        case_digest=conformance_case_digest(case),
        sql_digest="sql",
        rows=((1,),),
        session_facts=(("catalog", "main"),),
    )
    second = ExecutionObservation(
        runtime=first.runtime,
        case_digest=first.case_digest,
        sql_digest=first.sql_digest,
        rows=first.rows,
        session_facts=(("catalog", "other"),),
    )
    assert execution_observation_digest(first) != execution_observation_digest(second)


def test_bag_comparison_preserves_multiplicity() -> None:
    runtime = EngineRuntimeIdentity("sqlite", "sqlite-conformance-v1")
    left = ExecutionObservation(runtime, "case", "left", rows=((1,), (2,), (2,)))
    right = ExecutionObservation(runtime, "case", "right", rows=((2,), (1,), (2,)))
    result = compare_observations(left, right, ComparisonPolicy(ComparisonMode.BAG))
    assert result.state is ComparisonState.MATCH

    missing_duplicate = ExecutionObservation(runtime, "case", "right2", rows=((1,), (2,)))
    mismatch = compare_observations(
        left, missing_duplicate, ComparisonPolicy(ComparisonMode.BAG)
    )
    assert mismatch.state is ComparisonState.MISMATCH


def test_ordered_and_set_comparison_are_distinct() -> None:
    runtime = EngineRuntimeIdentity("sqlite", "sqlite-conformance-v1")
    left = ExecutionObservation(runtime, "case", "left", rows=((1,), (2,), (2,)))
    reordered = ExecutionObservation(runtime, "case", "right", rows=((2,), (1,), (2,)))
    assert compare_observations(
        left, reordered, ComparisonPolicy(ComparisonMode.ORDERED)
    ).state is ComparisonState.MISMATCH
    assert compare_observations(
        left, reordered, ComparisonPolicy(ComparisonMode.SET)
    ).state is ComparisonState.MATCH


def test_nondeterministic_policy_is_inconclusive() -> None:
    runtime = EngineRuntimeIdentity("sqlite", "sqlite-conformance-v1")
    observation = ExecutionObservation(runtime, "case", "sql", rows=((1,),))
    result = compare_observations(
        observation,
        observation,
        ComparisonPolicy(ComparisonMode.ORDERED, allow_nondeterminism=True),
    )
    assert result.state is ComparisonState.INCONCLUSIVE
