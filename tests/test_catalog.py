import sql_connectome.connectome as connectome


def test_default_catalog_is_public_and_resolves_existing_aliases() -> None:
    catalog = getattr(connectome, "DEFAULT_CATALOG", None)

    assert catalog is not None
    assert catalog.resolve("postgresql").dialect_id == "postgresql"
    assert catalog.resolve("postgres").dialect_id == "postgresql"
    assert catalog.parser_adapter("postgresql") == "postgres"
