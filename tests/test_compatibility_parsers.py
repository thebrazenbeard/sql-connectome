import pytest

import sql_connectome.connectome as connectome


@pytest.mark.parametrize(
    ("dialect_id", "parser"),
    (
        ("cockroachdb", "postgres"),
        ("tidb", "mysql"),
        ("yugabyte_ysql", "postgres"),
        ("cratedb", "postgres"),
        ("questdb", "postgres"),
    ),
)
def test_evidence_backed_compatibility_parsers_are_admitted(
    dialect_id: str,
    parser: str,
) -> None:
    genome = connectome.DEFAULT_CATALOG.resolve(dialect_id)

    assert genome.coverage.parser.value == "COMPATIBILITY_ADAPTER"
    assert genome.coverage.semantics.value == "NOT_ESTABLISHED"
    assert genome.coverage.translation.value == "NOT_ESTABLISHED"
    assert genome.coverage.behavior.value == "NOT_ESTABLISHED"
    assert connectome.DEFAULT_CATALOG.parser_adapter(dialect_id) == parser


@pytest.mark.parametrize(
    "dialect_id",
    ("cockroachdb", "tidb", "yugabyte_ysql", "cratedb", "questdb"),
)
def test_compatibility_parsers_handle_portable_select_without_promoting_semantics(
    dialect_id: str,
) -> None:
    parsed = connectome.parse_sql_text("SELECT 1 AS value", dialect_id)

    assert parsed.ir.source_dialect == dialect_id
    assert connectome.DEFAULT_CATALOG.resolve(dialect_id).coverage.semantics.value == (
        "NOT_ESTABLISHED"
    )


@pytest.mark.parametrize(
    "dialect_id",
    ("cockroachdb", "tidb", "yugabyte_ysql", "cratedb", "questdb"),
)
def test_compatibility_parser_reports_semantic_gap_and_binding_fails_closed(
    dialect_id: str,
) -> None:
    parsed = connectome.parse_sql_text("SELECT 1 AS value", dialect_id)
    payload = parsed.as_dict()

    assert payload["semantic_admission"] == {
        "state": "UNADMITTED_CAPABILITIES_PRESENT",
        "admitted_capabilities": [],
        "unadmitted_capabilities": ["relational_select"],
    }

    with pytest.raises(
        connectome.SQLTextError,
        match="BINDING_SOURCE_CAPABILITY_NOT_ADMITTED:relational_select",
    ):
        connectome.bind_sql_text(
            "SELECT id FROM users",
            dialect_id,
            {"users": {"id": "INT"}},
        )


def test_translation_from_parser_only_dialect_fails_at_semantic_gate() -> None:
    with pytest.raises(
        connectome.SQLTextError,
        match="SOURCE_CAPABILITY_NOT_ADMITTED:relational_select",
    ):
        connectome.transpile_sql_text(
            "SELECT 1 AS value",
            "cockroachdb",
            "postgresql",
        )
