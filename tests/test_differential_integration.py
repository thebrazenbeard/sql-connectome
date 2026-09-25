import os

import pytest

from sql_connectome.config import get_settings
from sql_connectome.differential import DifferentialProbe, run_differential_conformance


@pytest.mark.skipif(
    not os.getenv("SQL_CONNECTOME_DATABASE_URL"),
    reason="SQL_CONNECTOME_DATABASE_URL not set",
)
def test_three_engine_portable_probe_agrees() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    probe = DifferentialProbe(
        probe_id="three_engine_integer_addition",
        sql="SELECT 1 + 2 AS value",
        purpose="Three-engine portable arithmetic baseline.",
    )

    payload = run_differential_conformance(
        settings=settings,
        probes=(probe,),
        source_commit="integration-test",
    )

    assert payload["postgresql_included"] is True
    result = payload["results"][0]
    assert result["execution_outcome"] == "ALL_PASS"
    assert result["value_outcome"] == "AGREE"
    assert result["type_outcome"] == "AGREE"

    engines = {row["engine"]: row for row in result["engines"]}
    assert set(engines) == {"duckdb", "sqlite", "postgresql"}
    assert all(row["status"] == "PASS" for row in engines.values())
    assert engines["postgresql"]["runtime"]["identity_digest"]
