from __future__ import annotations

from enum import StrEnum

from .model import DialectGenome


class SQLStandardPart(StrEnum):
    FRAMEWORK = "framework"
    FOUNDATION = "foundation"
    CLI = "cli"
    PSM = "psm"
    MED = "med"
    OLB = "olb"
    SCHEMATA = "schemata"
    JRT = "jrt"
    XML = "xml"
    MDA = "mda"
    PGQ = "pgq"


class SQLFeatureFamily(StrEnum):
    RELATIONAL_QUERY = "relational_query"
    DATA_DEFINITION = "data_definition"
    DATA_MODIFICATION = "data_modification"
    TYPE_SYSTEM = "type_system"
    CONSTRAINTS = "constraints"
    TRANSACTIONS_LOCKING = "transactions_locking"
    PROCEDURAL_ROUTINES = "procedural_routines"
    SESSION_CONTROL = "session_control"
    SECURITY_AUTHORIZATION = "security_authorization"
    METADATA_SCHEMATA = "metadata_schemata"
    EXTERNAL_DATA_FEDERATION = "external_data_federation"
    JSON_DOCUMENT = "json_document"
    XML = "xml"
    NESTED_COLLECTIONS = "nested_collections"
    ANALYTICS = "analytics"
    GEOSPATIAL = "geospatial"
    PROPERTY_GRAPH = "property_graph"
    MULTIDIMENSIONAL = "multidimensional"
    VECTOR = "vector"
    STREAMING_INCREMENTAL = "streaming_incremental"
    ADMINISTRATION = "administration"


CAPABILITY_FEATURE_FAMILY: dict[str, SQLFeatureFamily] = {
    "apply": SQLFeatureFamily.RELATIONAL_QUERY,
    "arrays": SQLFeatureFamily.NESTED_COLLECTIONS,
    "connect_by": SQLFeatureFamily.RELATIONAL_QUERY,
    "cte": SQLFeatureFamily.RELATIONAL_QUERY,
    "derived_tables": SQLFeatureFamily.RELATIONAL_QUERY,
    "federation": SQLFeatureFamily.EXTERNAL_DATA_FEDERATION,
    "geospatial": SQLFeatureFamily.GEOSPATIAL,
    "json": SQLFeatureFamily.JSON_DOCUMENT,
    "lateral_join": SQLFeatureFamily.RELATIONAL_QUERY,
    "maps": SQLFeatureFamily.NESTED_COLLECTIONS,
    "materialized_views": SQLFeatureFamily.DATA_DEFINITION,
    "merge": SQLFeatureFamily.DATA_MODIFICATION,
    "objects": SQLFeatureFamily.JSON_DOCUMENT,
    "pivot": SQLFeatureFamily.ANALYTICS,
    "qualify": SQLFeatureFamily.ANALYTICS,
    "recursive_cte": SQLFeatureFamily.RELATIONAL_QUERY,
    "relational_select": SQLFeatureFamily.RELATIONAL_QUERY,
    "returning": SQLFeatureFamily.DATA_MODIFICATION,
    "rows": SQLFeatureFamily.NESTED_COLLECTIONS,
    "scripting": SQLFeatureFamily.PROCEDURAL_ROUTINES,
    "stored_procedures": SQLFeatureFamily.PROCEDURAL_ROUTINES,
    "structs": SQLFeatureFamily.NESTED_COLLECTIONS,
    "top": SQLFeatureFamily.RELATIONAL_QUERY,
    "transactions": SQLFeatureFamily.TRANSACTIONS_LOCKING,
    "unpivot": SQLFeatureFamily.ANALYTICS,
    "variant": SQLFeatureFamily.JSON_DOCUMENT,
    "window_functions": SQLFeatureFamily.ANALYTICS,
}

STANDARD_PART_FAMILIES: dict[SQLStandardPart, frozenset[SQLFeatureFamily]] = {
    SQLStandardPart.FRAMEWORK: frozenset(),
    SQLStandardPart.FOUNDATION: frozenset(
        {
            SQLFeatureFamily.RELATIONAL_QUERY,
            SQLFeatureFamily.DATA_DEFINITION,
            SQLFeatureFamily.DATA_MODIFICATION,
            SQLFeatureFamily.TYPE_SYSTEM,
            SQLFeatureFamily.CONSTRAINTS,
            SQLFeatureFamily.TRANSACTIONS_LOCKING,
            SQLFeatureFamily.SESSION_CONTROL,
            SQLFeatureFamily.SECURITY_AUTHORIZATION,
            SQLFeatureFamily.ANALYTICS,
        }
    ),
    SQLStandardPart.CLI: frozenset(),
    SQLStandardPart.PSM: frozenset({SQLFeatureFamily.PROCEDURAL_ROUTINES}),
    SQLStandardPart.MED: frozenset({SQLFeatureFamily.EXTERNAL_DATA_FEDERATION}),
    SQLStandardPart.OLB: frozenset(),
    SQLStandardPart.SCHEMATA: frozenset({SQLFeatureFamily.METADATA_SCHEMATA}),
    SQLStandardPart.JRT: frozenset({SQLFeatureFamily.PROCEDURAL_ROUTINES}),
    SQLStandardPart.XML: frozenset({SQLFeatureFamily.XML}),
    SQLStandardPart.MDA: frozenset({SQLFeatureFamily.MULTIDIMENSIONAL}),
    SQLStandardPart.PGQ: frozenset({SQLFeatureFamily.PROPERTY_GRAPH}),
}


def feature_family_manifest(genome: DialectGenome) -> dict[str, object]:
    capabilities_by_family: dict[SQLFeatureFamily, list[str]] = {
        family: [] for family in SQLFeatureFamily
    }
    unclassified: list[str] = []
    for capability in sorted(genome.capabilities):
        family = CAPABILITY_FEATURE_FAMILY.get(capability)
        if family is None:
            unclassified.append(capability)
        else:
            capabilities_by_family[family].append(capability)

    return {
        "schema": "SQL_CONNECTOME_FEATURE_FAMILY_COVERAGE_V1",
        "dialect_id": genome.dialect_id,
        "families": [
            {
                "family": family.value,
                "state": (
                    "MODELED_CAPABILITIES"
                    if capabilities_by_family[family]
                    else "NOT_MODELED"
                ),
                "capabilities": capabilities_by_family[family],
            }
            for family in SQLFeatureFamily
        ],
        "unclassified_capabilities": unclassified,
    }
