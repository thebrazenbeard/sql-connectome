from sql_connectome.conformance import ComparisonMode, ComparisonPolicy, ConformanceCase
from sql_connectome.conformance_runners import DuckDBRunner, SQLiteRunner
from sql_connectome.metamorphic import qualify_rewrite


def test_redundant_project_case_is_case_bound_not_universal() -> None:
    case = ConformanceCase(
        case_id="redundant-project-1",
        seed=11,
        setup_sql=("CREATE TABLE t(a INTEGER)", "INSERT INTO t VALUES (1), (2), (2)"),
        source_sql="SELECT a FROM t",
        transformed_sql="SELECT a FROM (SELECT a FROM t) q",
        comparison_policy=ComparisonPolicy(ComparisonMode.BAG),
        invariant=True,
        assumptions=("identity projection",),
    )
    report = qualify_rewrite(
        rewrite_id="redundant-project-elimination",
        rewrite_version="1",
        rewrite_application_digest="application",
        case=case,
        runners=(SQLiteRunner(), DuckDBRunner()),
    )
    assert report.qualification == "BEHAVIORALLY_QUALIFIED_CASE_BOUND"
    assert report.counterexamples == ()
    assert {item[0] for item in report.engine_results} == {"sqlite", "duckdb"}


def test_mismatch_is_retained_as_counterexample() -> None:
    case = ConformanceCase(
        case_id="bad-rewrite",
        seed=12,
        setup_sql=("CREATE TABLE t(a INTEGER)", "INSERT INTO t VALUES (1), (2)"),
        source_sql="SELECT a FROM t",
        transformed_sql="SELECT a FROM t WHERE a = 1",
        comparison_policy=ComparisonPolicy(ComparisonMode.BAG),
    )
    report = qualify_rewrite(
        rewrite_id="bad",
        rewrite_version="1",
        rewrite_application_digest="application",
        case=case,
        runners=(SQLiteRunner(), DuckDBRunner()),
    )
    assert report.qualification == "NOT_QUALIFIED"
    assert len(report.counterexamples) == 2
