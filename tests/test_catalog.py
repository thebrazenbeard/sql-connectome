import pytest

import sql_connectome.connectome as connectome
from sql_connectome.connectome import (
    ConnectomeCatalog,
    DialectGenome,
    SemanticDimension,
    parse_sql_text,
)


def test_default_catalog_is_public_and_resolves_existing_aliases() -> None:
    catalog = getattr(connectome, "DEFAULT_CATALOG", None)

    assert catalog is not None
    assert catalog.resolve("postgresql").dialect_id == "postgresql"
    assert catalog.resolve("postgres").dialect_id == "postgresql"
    assert catalog.parser_adapter("postgresql") == "postgres"


def test_catalog_rejects_alias_collision() -> None:
    alpha = DialectGenome(
        dialect_id="alpha",
        family="test",
        engine="Alpha",
        version_selector="test",
        capabilities=frozenset({"relational_select"}),
        semantic_dimensions=frozenset({SemanticDimension.RELATIONAL}),
        aliases=frozenset({"shared"}),
    )
    beta = DialectGenome(
        dialect_id="beta",
        family="test",
        engine="Beta",
        version_selector="test",
        capabilities=frozenset({"relational_select"}),
        semantic_dimensions=frozenset({SemanticDimension.RELATIONAL}),
        aliases=frozenset({"shared"}),
    )

    with pytest.raises(ValueError, match="CATALOG_ALIAS_COLLISION:shared"):
        ConnectomeCatalog(
            dialects={"alpha": alpha, "beta": beta},
            parser_adapters={"alpha": "postgres", "beta": "postgres"},
            rewrite_rules=(),
        )


def test_custom_catalog_can_drive_parser_admission() -> None:
    genome = DialectGenome(
        dialect_id="pgish",
        family="postgres-family",
        engine="PG-ish test dialect",
        version_selector="test",
        capabilities=frozenset({"relational_select"}),
        semantic_dimensions=frozenset({SemanticDimension.RELATIONAL}),
        aliases=frozenset({"pgx"}),
    )
    catalog = ConnectomeCatalog(
        dialects={"pgish": genome},
        parser_adapters={"pgish": "postgres"},
        rewrite_rules=(),
    )

    parsed = parse_sql_text("SELECT 1 AS one", "pgx", catalog=catalog)

    assert parsed.ir.source_dialect == "pgish"
    assert parsed.parser_dialect == "postgres"


def test_catalog_admission_returns_new_catalog_without_mutating_source() -> None:
    base = ConnectomeCatalog(dialects={}, parser_adapters={}, rewrite_rules=())
    genome = DialectGenome(
        dialect_id="pgish",
        family="postgres-family",
        engine="PG-ish test dialect",
        version_selector="test",
        capabilities=frozenset({"relational_select"}),
        semantic_dimensions=frozenset({SemanticDimension.RELATIONAL}),
        aliases=frozenset({"pgx"}),
    )

    extended = base.admit_dialect(genome, parser_adapter="postgres")

    assert "pgish" not in base.dialects
    assert extended.resolve("pgx") is genome
    assert extended.parser_adapter("pgish") == "postgres"
