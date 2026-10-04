from sql_connectome.connectome import DEFAULT_CATALOG
from sql_connectome.connectome.feature_families import (
    CAPABILITY_FEATURE_FAMILY,
    STANDARD_PART_FAMILIES,
    SQLFeatureFamily,
    SQLStandardPart,
    feature_family_manifest,
)


def test_every_default_capability_is_classified_into_a_feature_family() -> None:
    capabilities = {
        capability
        for genome in DEFAULT_CATALOG.dialects.values()
        for capability in genome.capabilities
    }

    assert capabilities <= set(CAPABILITY_FEATURE_FAMILY)


def test_postgresql_feature_manifest_separates_modeled_and_unmodeled_families() -> None:
    manifest = feature_family_manifest(DEFAULT_CATALOG.resolve("postgresql"))
    by_family = {row["family"]: row for row in manifest["families"]}

    assert by_family["relational_query"]["state"] == "MODELED_CAPABILITIES"
    assert "recursive_cte" in by_family["relational_query"]["capabilities"]
    assert by_family["transactions_locking"]["state"] == "MODELED_CAPABILITIES"
    assert by_family["property_graph"]["state"] == "NOT_MODELED"
def test_sql_2023_module_alignment_keeps_future_surfaces_visible() -> None:
    assert SQLFeatureFamily.PROPERTY_GRAPH in STANDARD_PART_FAMILIES[
        SQLStandardPart.PGQ
    ]
    assert SQLFeatureFamily.MULTIDIMENSIONAL in STANDARD_PART_FAMILIES[
        SQLStandardPart.MDA
    ]
    assert SQLFeatureFamily.XML in STANDARD_PART_FAMILIES[
        SQLStandardPart.XML
    ]
    assert SQLFeatureFamily.PROCEDURAL_ROUTINES in STANDARD_PART_FAMILIES[
        SQLStandardPart.PSM
    ]


def test_known_unparsed_dialect_has_no_modeled_feature_families() -> None:
    manifest = feature_family_manifest(DEFAULT_CATALOG.resolve("db2"))

    assert all(row["state"] == "NOT_MODELED" for row in manifest["families"])


def test_catalog_manifest_binds_feature_family_coverage() -> None:
    manifest = DEFAULT_CATALOG.manifest()
    postgres = next(
        row for row in manifest["dialects"] if row["dialect_id"] == "postgresql"
    )

    coverage = postgres["feature_family_coverage"]
    assert coverage["schema"] == "SQL_CONNECTOME_FEATURE_FAMILY_COVERAGE_V1"
    assert coverage["dialect_id"] == "postgresql"



def test_public_dialect_inventory_exposes_feature_family_coverage() -> None:
    from sql_connectome.connectome import list_dialects

    postgres = next(
        row for row in list_dialects() if row["dialect_id"] == "postgresql"
    )

    coverage = postgres["feature_family_coverage"]
    by_family = {row["family"]: row for row in coverage["families"]}
    assert by_family["data_modification"]["state"] == "MODELED_CAPABILITIES"
    assert by_family["xml"]["state"] == "NOT_MODELED"
