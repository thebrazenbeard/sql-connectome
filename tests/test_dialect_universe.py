import pytest

import sql_connectome.connectome as connectome
import sql_connectome.connectome.registry as registry


def test_researched_sql_universe_is_explicitly_cataloged() -> None:
    expected = {
        "flink",
        "ksqldb",
        "spanner_googlesql",
        "spanner_postgresql",
        "informix",
        "netezza",
        "h2",
        "pinot",
        "cratedb",
        "questdb",
    }
    assert expected <= set(connectome.DEFAULT_CATALOG.dialects)


def test_unimplemented_researched_dialects_fail_closed_without_overclaiming() -> None:
    for dialect_id in {
        "flink",
        "ksqldb",
        "informix",
        "netezza",
        "h2",
        "pinot",
        "cratedb",
        "questdb",
    }:
        genome = connectome.DEFAULT_CATALOG.resolve(dialect_id)
        assert genome.coverage.parser.value == "NOT_AVAILABLE"
        assert genome.coverage.semantics.value == "NOT_ESTABLISHED"
        assert genome.coverage.translation.value == "NOT_ESTABLISHED"
        assert genome.coverage.behavior.value == "NOT_ESTABLISHED"
        with pytest.raises(KeyError, match="PARSER_ADAPTER_NOT_CONFIGURED"):
            connectome.DEFAULT_CATALOG.parser_adapter(dialect_id)


def test_spanner_dialects_use_only_compatibility_parsers() -> None:
    google = connectome.DEFAULT_CATALOG.resolve("spanner_googlesql")
    postgres = connectome.DEFAULT_CATALOG.resolve("spanner_postgresql")

    assert google.coverage.parser.value == "COMPATIBILITY_ADAPTER"
    assert postgres.coverage.parser.value == "COMPATIBILITY_ADAPTER"
    assert connectome.DEFAULT_CATALOG.parser_adapter("spanner_googlesql") == "bigquery"
    assert connectome.DEFAULT_CATALOG.parser_adapter("spanner_postgresql") == "postgres"
    assert google.coverage.semantics.value == "NOT_ESTABLISHED"
    assert postgres.coverage.semantics.value == "NOT_ESTABLISHED"


def test_soql_is_classified_as_sql_like_but_not_an_sql_dialect() -> None:
    assert "soql" in registry.SQL_LIKE_NON_SQL_LANGUAGES
    with pytest.raises(KeyError, match="UNKNOWN_DIALECT:soql"):
        connectome.DEFAULT_CATALOG.resolve("soql")
