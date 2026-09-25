import pytest

import sql_connectome.connectome as connectome
from sql_connectome.connectome import (
    ConnectomeCatalog,
    DialectGenome,
    RewriteRule,
    SQLTextError,
    SemanticDimension,
    TranslationFidelity,
    inspect_sql_contracts,
    inspect_type_system,
    list_dialects,
    parse_sql_text,
    probe_sql_dialects,
    transpile_sql_text,
)


def _genome(
    dialect_id: str,
    *,
    parser_family: str = "test",
    capabilities: frozenset[str] = frozenset({"relational_select"}),
    aliases: frozenset[str] = frozenset(),
) -> DialectGenome:
    return DialectGenome(
        dialect_id=dialect_id,
        family=parser_family,
        engine=f"{dialect_id} test engine",
        version_selector="test",
        capabilities=capabilities,
        semantic_dimensions=frozenset({SemanticDimension.RELATIONAL}),
        aliases=aliases,
    )


def test_default_catalog_is_public_and_resolves_existing_aliases() -> None:
    catalog = getattr(connectome, "DEFAULT_CATALOG", None)

    assert catalog is not None
    assert catalog.resolve("postgresql").dialect_id == "postgresql"
    assert catalog.resolve("postgres").dialect_id == "postgresql"
    assert catalog.parser_adapter("postgresql") == "postgres"


def test_catalog_is_immutable_and_resolves_normalized_aliases() -> None:
    genome = _genome("pgish", aliases=frozenset({"PGX"}))
    catalog = ConnectomeCatalog(
        dialects={"pgish": genome},
        parser_adapters={"pgish": "postgres"},
        rewrite_rules=(),
    )

    assert catalog.resolve(" pgx ").dialect_id == "pgish"

    with pytest.raises(TypeError):
        catalog.dialects["other"] = genome  # type: ignore[index]

    with pytest.raises(TypeError):
        catalog.parser_adapters["pgish"] = "mysql"  # type: ignore[index]


def test_catalog_rejects_alias_collision() -> None:
    alpha = _genome("alpha", aliases=frozenset({"shared"}))
    beta = _genome("beta", aliases=frozenset({"shared"}))

    with pytest.raises(ValueError, match="CATALOG_ALIAS_COLLISION:shared"):
        ConnectomeCatalog(
            dialects={"alpha": alpha, "beta": beta},
            parser_adapters={"alpha": "postgres", "beta": "postgres"},
            rewrite_rules=(),
        )


def test_catalog_rejects_orphan_parser_adapter() -> None:
    with pytest.raises(ValueError, match="CATALOG_ORPHAN_PARSER_ADAPTER:other"):
        ConnectomeCatalog(
            dialects={"pgish": _genome("pgish")},
            parser_adapters={"other": "postgres"},
            rewrite_rules=(),
        )


def test_custom_catalog_drives_parser_contract_type_probe_and_inventory() -> None:
    genome = _genome("pgish", aliases=frozenset({"pgx"}))
    catalog = ConnectomeCatalog(
        dialects={"pgish": genome},
        parser_adapters={"pgish": "postgres"},
        rewrite_rules=(),
    )

    parsed = parse_sql_text("SELECT 1 AS one", "pgx", catalog=catalog)
    contracts = inspect_sql_contracts("SELECT ABS(1)", "pgx", catalog=catalog)
    type_graph = inspect_type_system("pgx", catalog=catalog)
    probe = probe_sql_dialects("SELECT 1", max_candidates=1, catalog=catalog)
    inventory = list_dialects(dialects=catalog.dialects)

    assert parsed.ir.source_dialect == "pgish"
    assert parsed.parser_dialect == "postgres"
    assert contracts["dialect_id"] == "pgish"
    assert type_graph["dialect_id"] == "pgish"
    assert probe["candidate_count"] == 1
    assert probe["candidates"][0]["dialect_id"] == "pgish"
    assert [row["dialect_id"] for row in inventory] == ["pgish"]

    with pytest.raises(KeyError, match="UNKNOWN_DIALECT:mysql"):
        catalog.resolve("mysql")


def test_custom_catalog_can_drive_translation_and_rewrite_admission() -> None:
    source = _genome(
        "sourceish",
        parser_family="duckdb-family",
        capabilities=frozenset(
            {"relational_select", "window_functions", "qualify"}
        ),
    )
    target = _genome(
        "targetish",
        parser_family="postgres-family",
        capabilities=frozenset(
            {"relational_select", "window_functions", "derived_tables"}
        ),
    )
    rule = RewriteRule(
        name="test-qualify-via-derived-table",
        source_capability="qualify",
        target_capabilities=frozenset({"window_functions", "derived_tables"}),
        fidelity=TranslationFidelity.CONSTRUCTIVE,
        description="Test-only QUALIFY rewrite admission.",
    )
    catalog = ConnectomeCatalog(
        dialects={"sourceish": source, "targetish": target},
        parser_adapters={"sourceish": "duckdb", "targetish": "postgres"},
        rewrite_rules=(rule,),
    )

    result = transpile_sql_text(
        "SELECT x, ROW_NUMBER() OVER () AS rn FROM t QUALIFY rn = 1",
        "sourceish",
        "targetish",
        catalog=catalog,
    )

    assert result["source"]["ir"]["source_dialect"] == "sourceish"
    assert result["target_parse"]["ir"]["source_dialect"] == "targetish"
    assert result["plan"]["fidelity"] == "CONSTRUCTIVE"
    assert [row["rule_name"] for row in result["plan"]["rewrites"]] == [
        "test-qualify-via-derived-table"
    ]


def test_catalog_without_parser_adapter_fails_closed() -> None:
    catalog = ConnectomeCatalog(
        dialects={"pgish": _genome("pgish")},
        parser_adapters={},
        rewrite_rules=(),
    )

    with pytest.raises(SQLTextError, match="PARSER_ADAPTER_NOT_CONFIGURED:pgish"):
        parse_sql_text("SELECT 1", "pgish", catalog=catalog)
