import pytest

from sql_connectome.connectome import (
    SQLTextError,
    dialect_semantic_profile,
    transpile_sql_text,
)


def test_semantic_profiles_expose_null_function_behavior() -> None:
    mysql = dialect_semantic_profile("mysql", "mysql")
    postgres = dialect_semantic_profile("postgresql", "postgres")

    assert mysql["flags"]["least_greatest_ignores_nulls"] is False
    assert postgres["flags"]["least_greatest_ignores_nulls"] is True


def test_least_null_semantics_prevent_false_exact_translation() -> None:
    with pytest.raises(SQLTextError, match="LOSSY_TRANSLATION_REQUIRES_OPT_IN"):
        transpile_sql_text(
            "SELECT LEAST(score, fallback_score) FROM results",
            "mysql",
            "postgresql",
        )


def test_least_null_semantics_are_reported_with_opt_in() -> None:
    result = transpile_sql_text(
        "SELECT LEAST(score, fallback_score) FROM results",
        "mysql",
        "postgresql",
        allow_lossy=True,
    )

    assert result["plan"]["fidelity"] == "EXACT"
    assert result["combined_fidelity"] == "LOSSY"
    risks = result["expression_semantics"]["risks"]
    assert {risk["code"] for risk in risks} == {"LEAST_GREATEST_NULL_SEMANTICS"}
    assert result["expression_semantics"]["risk_count"] == 1


def test_division_by_zero_semantics_are_detected() -> None:
    result = transpile_sql_text(
        "SELECT numerator / denominator FROM measurements",
        "mysql",
        "postgresql",
        allow_lossy=True,
    )

    risk_codes = {risk["code"] for risk in result["expression_semantics"]["risks"]}
    assert "DIVISION_BY_ZERO_SEMANTICS" in risk_codes
    assert result["combined_fidelity"] == "LOSSY"


def test_unaffected_query_retains_exact_expression_ceiling() -> None:
    result = transpile_sql_text(
        "SELECT id, COUNT(*) AS n FROM events GROUP BY id",
        "mysql",
        "postgresql",
    )

    assert result["plan"]["fidelity"] == "EXACT"
    assert result["combined_fidelity"] == "EXACT"
    assert result["expression_semantics"]["risk_count"] == 0
    function_names = {
        row["name"] for row in result["expression_semantics"]["inventory"]["functions"]
    }
    assert "COUNT" in function_names
