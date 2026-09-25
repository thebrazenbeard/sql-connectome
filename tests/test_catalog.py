import pytest

import sql_connectome.connectome as connectome
from sql_connectome.connectome import ConnectomeCatalog, DialectGenome, SemanticDimension


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
