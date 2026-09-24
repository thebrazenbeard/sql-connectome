import pytest

from sql_connectome.connectome import SQLTextError, list_dialects, probe_sql_dialects


def test_registry_exposes_expanded_sql_family_coverage() -> None:
    ids = {item["dialect_id"] for item in list_dialects()}

    assert len(ids) >= 28
    assert {
        "athena",
        "clickhouse",
        "databricks",
        "hive",
        "materialize",
        "presto",
        "redshift",
        "spark",
        "teradata",
    }.issubset(ids)


def test_tsql_top_produces_strong_tsql_evidence() -> None:
    result = probe_sql_dialects("SELECT TOP 10 * FROM users", max_candidates=5)

    assert result["identity_proof"] is False
    assert result["candidates"][0]["dialect_id"] == "tsql"
    assert result["candidates"][0]["score"] >= 7
    assert "SELECT TOP:+5" in result["candidates"][0]["evidence"]
    assert result["ambiguous"] is False


def test_generic_select_remains_ambiguous() -> None:
    result = probe_sql_dialects("SELECT 1", max_candidates=8)

    assert result["candidate_count"] > 1
    assert result["ambiguous"] is True
    assert len({item["score"] for item in result["candidates"][:2]}) == 1


def test_snowflake_variant_marker_is_evidence_not_identity_proof() -> None:
    result = probe_sql_dialects(
        "SELECT CAST('1' AS VARIANT) AS value",
        max_candidates=5,
    )

    assert result["candidates"][0]["dialect_id"] == "snowflake"
    assert result["candidates"][0]["score"] >= 7
    assert result["identity_proof"] is False


def test_probe_rejects_invalid_candidate_bound() -> None:
    with pytest.raises(SQLTextError, match="INVALID_MAX_CANDIDATES"):
        probe_sql_dialects("SELECT 1", max_candidates=0)
