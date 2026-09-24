from __future__ import annotations

from .model import DialectGenome, RewriteRule, SemanticDimension, TranslationFidelity


def _genome(
    dialect_id: str,
    family: str,
    engine: str,
    version_selector: str,
    capabilities: set[str],
    dimensions: set[SemanticDimension],
    aliases: set[str] | None = None,
    notes: tuple[str, ...] = (),
) -> DialectGenome:
    return DialectGenome(
        dialect_id=dialect_id,
        family=family,
        engine=engine,
        version_selector=version_selector,
        capabilities=frozenset(capabilities),
        semantic_dimensions=frozenset(dimensions),
        aliases=frozenset(aliases or set()),
        notes=notes,
    )


# This is deliberately a conservative bootstrap registry, not a conformance matrix.
# Capabilities are admitted only when the semantic core needs them for a rule or test.
DEFAULT_DIALECTS: dict[str, DialectGenome] = {
    "postgresql": _genome(
        "postgresql",
        "postgres",
        "PostgreSQL",
        "16+",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "lateral_join",
            "returning",
            "merge",
            "arrays",
            "json",
            "materialized_views",
            "stored_procedures",
            "transactions",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.NESTED,
            SemanticDimension.DOCUMENT_JSON,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.TRANSACTIONAL,
            SemanticDimension.PROCEDURAL,
        },
        {"postgres", "pgsql"},
    ),
    "duckdb": _genome(
        "duckdb",
        "duckdb",
        "DuckDB",
        "1.x",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "qualify",
            "lateral_join",
            "arrays",
            "structs",
            "json",
            "pivot",
            "unpivot",
            "transactions",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.NESTED,
            SemanticDimension.DOCUMENT_JSON,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.TRANSACTIONAL,
        },
    ),
    "sqlite": _genome(
        "sqlite",
        "sqlite",
        "SQLite",
        "3.x",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "returning",
            "transactions",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.TRANSACTIONAL,
        },
    ),
    "mysql": _genome(
        "mysql",
        "mysql",
        "MySQL",
        "8.x",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "json",
            "stored_procedures",
            "transactions",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.DOCUMENT_JSON,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.TRANSACTIONAL,
            SemanticDimension.PROCEDURAL,
        },
    ),
    "bigquery": _genome(
        "bigquery",
        "google-sql",
        "BigQuery GoogleSQL",
        "current",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "qualify",
            "arrays",
            "structs",
            "json",
            "merge",
            "geospatial",
            "scripting",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.NESTED,
            SemanticDimension.DOCUMENT_JSON,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.GEOSPATIAL,
            SemanticDimension.PROCEDURAL,
        },
        {"googlesql"},
    ),
    "snowflake": _genome(
        "snowflake",
        "snowflake",
        "Snowflake SQL",
        "current",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "qualify",
            "variant",
            "arrays",
            "objects",
            "merge",
            "pivot",
            "unpivot",
            "geospatial",
            "materialized_views",
            "stored_procedures",
            "transactions",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.NESTED,
            SemanticDimension.DOCUMENT_JSON,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.GEOSPATIAL,
            SemanticDimension.TRANSACTIONAL,
            SemanticDimension.PROCEDURAL,
        },
    ),
    "tsql": _genome(
        "tsql",
        "transact-sql",
        "Microsoft SQL Server / T-SQL",
        "current",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "top",
            "apply",
            "pivot",
            "unpivot",
            "merge",
            "stored_procedures",
            "transactions",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.TRANSACTIONAL,
            SemanticDimension.PROCEDURAL,
        },
        {"sqlserver", "mssql"},
    ),
    "oracle": _genome(
        "oracle",
        "oracle",
        "Oracle Database SQL",
        "current",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "recursive_cte",
            "window_functions",
            "connect_by",
            "pivot",
            "unpivot",
            "merge",
            "returning",
            "json",
            "stored_procedures",
            "transactions",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.DOCUMENT_JSON,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.TRANSACTIONAL,
            SemanticDimension.PROCEDURAL,
        },
    ),
    "trino": _genome(
        "trino",
        "trino",
        "Trino SQL",
        "current",
        {
            "relational_select",
            "derived_tables",
            "cte",
            "window_functions",
            "arrays",
            "maps",
            "rows",
            "json",
            "geospatial",
            "federation",
        },
        {
            SemanticDimension.RELATIONAL,
            SemanticDimension.NESTED,
            SemanticDimension.DOCUMENT_JSON,
            SemanticDimension.ANALYTICAL,
            SemanticDimension.GEOSPATIAL,
            SemanticDimension.FEDERATED,
        },
        {"presto-compatible"},
    ),
}


DEFAULT_REWRITE_RULES: tuple[RewriteRule, ...] = (
    RewriteRule(
        name="qualify-via-derived-table",
        source_capability="qualify",
        target_capabilities=frozenset({"window_functions", "derived_tables"}),
        fidelity=TranslationFidelity.CONSTRUCTIVE,
        description=(
            "Materialize the windowed relation in a derived table/CTE and apply the QUALIFY "
            "predicate outside it."
        ),
    ),
    RewriteRule(
        name="apply-via-lateral",
        source_capability="apply",
        target_capabilities=frozenset({"lateral_join"}),
        fidelity=TranslationFidelity.CONSTRUCTIVE,
        description=(
            "Translate APPLY semantics through a lateral relation, preserving correlation "
            "when the source expression has no dialect-specific side effects."
        ),
    ),
    RewriteRule(
        name="connect-by-via-recursive-cte",
        source_capability="connect_by",
        target_capabilities=frozenset({"recursive_cte"}),
        fidelity=TranslationFidelity.LOSSY,
        description=(
            "Reconstruct hierarchy traversal with a recursive CTE. Oracle pseudocolumn, "
            "cycle, and sibling-order semantics require explicit handling and may not be exact."
        ),
    ),
    RewriteRule(
        name="variant-via-json",
        source_capability="variant",
        target_capabilities=frozenset({"json"}),
        fidelity=TranslationFidelity.LOSSY,
        description=(
            "Represent semi-structured VARIANT content as JSON. Typed-value and engine-specific "
            "comparison/coercion semantics are not guaranteed to survive."
        ),
    ),
    RewriteRule(
        name="struct-via-json",
        source_capability="structs",
        target_capabilities=frozenset({"json"}),
        fidelity=TranslationFidelity.LOSSY,
        description=(
            "Encode structured records as JSON when no native STRUCT/ROW equivalent is available."
        ),
    ),
)


def resolve_dialect(dialect_id_or_alias: str) -> DialectGenome:
    key = dialect_id_or_alias.strip().lower()
    if key in DEFAULT_DIALECTS:
        return DEFAULT_DIALECTS[key]

    for genome in DEFAULT_DIALECTS.values():
        if key in genome.aliases:
            return genome

    raise KeyError(f"UNKNOWN_DIALECT:{dialect_id_or_alias}")
