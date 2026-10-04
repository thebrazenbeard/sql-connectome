import os

import pytest

from sql_connectome.differential import DEFAULT_PROBES, run_differential_conformance
from sql_connectome.trino_engine import validate_trino_readonly

trino = pytest.importorskip('trino')


def test_trino_adapter_against_real_engine() -> None:
    host = os.getenv("SQL_CONNECTOME_TRINO_HOST")
    if not host:
        pytest.skip("SQL_CONNECTOME_TRINO_HOST not set")
    connection = trino.dbapi.connect(
        host=host,
        port=int(os.getenv("SQL_CONNECTOME_TRINO_PORT", "8080")),
        user="sql-connectome-ci",
        catalog="system",
        schema="runtime",
        http_scheme="http",
    )
    try:
        result = validate_trino_readonly("SELECT 1 AS value", connection=connection)
    finally:
        connection.close()
    assert result.status.value == "PASS"
    assert result.runtime.engine == "trino"
    assert result.runtime.version
    assert dict(result.runtime.facts)["catalog"] == "system"
    assert result.query_executed is False


def test_trino_participates_in_differential_matrix() -> None:
    host = os.getenv("SQL_CONNECTOME_TRINO_HOST")
    if not host:
        pytest.skip("SQL_CONNECTOME_TRINO_HOST not set")
    connection = trino.dbapi.connect(
        host=host,
        port=int(os.getenv("SQL_CONNECTOME_TRINO_PORT", "8080")),
        user="sql-connectome-ci",
        catalog="system",
        schema="runtime",
        http_scheme="http",
    )
    try:
        payload = run_differential_conformance(
            probes=DEFAULT_PROBES,
            dbapi_engines={
                "trino": (
                    connection,
                    {"engine": "trino", "qualification": "real-engine-ci"},
                )
            },
        )
    finally:
        connection.close()

    assert payload["dbapi_engines_included"] == ["trino"]
    assert payload["probe_count"] == len(DEFAULT_PROBES)
    assert all(
        any(engine["engine"] == "trino" for engine in result["engines"])
        for result in payload["results"]
    )
