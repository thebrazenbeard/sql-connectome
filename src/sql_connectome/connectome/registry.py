from __future__ import annotations

from .model import (
    BehavioralCoverage,
    DialectCoverage,
    DialectGenome,
    ParserCoverage,
    RewriteRule,
    SemanticCoverage,
    SemanticDimension,
    TranslationCoverage,
    TranslationFidelity,
)


def _genome(
    dialect_id: str,
    family: str,
    engine: str,
    version_selector: str,
    capabilities: set[str],
    dimensions: set[SemanticDimension],
    aliases: set[str] | None = None,
    notes: tuple[str, ...] = (),
    coverage: DialectCoverage | None = None,
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
        coverage=coverage or DialectCoverage(),
    )


_NATIVE_MODELED = DialectCoverage(
    parser=ParserCoverage.NATIVE_DIALECT,
    semantics=SemanticCoverage.MODELED_CAPABILITIES,
    translation=TranslationCoverage.CAPABILITY_PLANNING,
)
_NATIVE_REAL_DIFFERENTIAL = DialectCoverage(
    parser=ParserCoverage.NATIVE_DIALECT,
    semantics=SemanticCoverage.MODELED_CAPABILITIES,
    translation=TranslationCoverage.CAPABILITY_PLANNING,
    behavior=BehavioralCoverage.REAL_ENGINE_DIFFERENTIAL,
)
_NATIVE_EMBEDDED_DIFFERENTIAL = DialectCoverage(
    parser=ParserCoverage.NATIVE_DIALECT,
    semantics=SemanticCoverage.MODELED_CAPABILITIES,
    translation=TranslationCoverage.CAPABILITY_PLANNING,
    behavior=BehavioralCoverage.EMBEDDED_ENGINE_DIFFERENTIAL,
)
_NATIVE_RELATIONAL_BASELINE = DialectCoverage(
    parser=ParserCoverage.NATIVE_DIALECT,
    semantics=SemanticCoverage.RELATIONAL_BASELINE,
    translation=TranslationCoverage.CAPABILITY_PLANNING,
)
_COMPAT_REAL_RELATIONAL = DialectCoverage(
    parser=ParserCoverage.COMPATIBILITY_ADAPTER,
    semantics=SemanticCoverage.RELATIONAL_BASELINE,
    translation=TranslationCoverage.CAPABILITY_PLANNING,
    behavior=BehavioralCoverage.REAL_ENGINE_DIFFERENTIAL,
)
_COMPAT_UNESTABLISHED = DialectCoverage(
    parser=ParserCoverage.COMPATIBILITY_ADAPTER,
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
        coverage=_NATIVE_REAL_DIFFERENTIAL,
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
        coverage=_NATIVE_EMBEDDED_DIFFERENTIAL,
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
        coverage=_NATIVE_EMBEDDED_DIFFERENTIAL,
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
        coverage=_NATIVE_REAL_DIFFERENTIAL,
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
        coverage=_NATIVE_MODELED,
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
        coverage=_NATIVE_MODELED,
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
        coverage=_NATIVE_MODELED,
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
        coverage=_NATIVE_MODELED,
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
        coverage=_NATIVE_REAL_DIFFERENTIAL,
    ),
    "mariadb": _genome(
        "mariadb",
        "mysql-family",
        "MariaDB",
        "11.x",
        {"relational_select"},
        {SemanticDimension.RELATIONAL},
        notes=(
            "Uses the SQLGlot MySQL parser as a compatibility adapter; "
            "MariaDB-specific syntax and semantics require separate qualification.",
        ),
        coverage=_COMPAT_REAL_RELATIONAL,
    ),
    "spanner_googlesql": _genome(
        "spanner_googlesql",
        "googlesql-family",
        "Google Cloud Spanner GoogleSQL",
        "current",
        set(),
        set(),
        {"spanner-google-sql"},
        notes=(
            "Uses SQLGlot BigQuery only as a GoogleSQL-family compatibility parser. "
            "Spanner-specific SQL and semantics remain unqualified.",
        ),
        coverage=_COMPAT_UNESTABLISHED,
    ),
    "spanner_postgresql": _genome(
        "spanner_postgresql",
        "postgres-family",
        "Google Cloud Spanner PostgreSQL interface",
        "current",
        set(),
        set(),
        {"spanner-pg", "spanner-postgres"},
        notes=(
            "Uses SQLGlot PostgreSQL only as a compatibility parser. "
            "Spanner documents a PostgreSQL subset plus Spanner extensions.",
        ),
        coverage=_COMPAT_UNESTABLISHED,
    ),
}

NON_SQL_SQLGLOT_DIALECTS = frozenset({"dax", "prql", "tableau"})
SQL_LIKE_NON_SQL_LANGUAGES = frozenset({"soql"})

# SQLGlot-backed parser coverage can be broader than our admitted semantic capability coverage.
# These genomes intentionally begin with only relational SELECT semantics. Dialect-specific
# capabilities are added separately as evidence and tests justify them.
_BASELINE_SQLGLOT_DIALECTS: dict[str, tuple[str, str, str, set[str]]] = {
    "athena": ("presto-family", "Amazon Athena SQL", "current", set()),
    "clickhouse": ("clickhouse", "ClickHouse SQL", "current", set()),
    "databricks": ("spark-family", "Databricks SQL", "current", set()),
    "doris": ("mysql-family", "Apache Doris SQL", "current", set()),
    "dremio": ("dremio", "Dremio SQL", "current", set()),
    "drill": ("drill", "Apache Drill SQL", "current", set()),
    "druid": ("druid", "Apache Druid SQL", "current", set()),
    "dune": ("dune", "DuneSQL", "current", set()),
    "exasol": ("exasol", "Exasol SQL", "current", set()),
    "fabric": ("transact-sql", "Microsoft Fabric SQL", "current", set()),
    "hive": ("hive", "Apache HiveQL", "current", {"hiveql"}),
    "materialize": ("postgres-family", "Materialize SQL", "current", set()),
    "presto": ("presto", "Presto SQL", "current", set()),
    "redshift": ("postgres-family", "Amazon Redshift SQL", "current", set()),
    "risingwave": ("postgres-family", "RisingWave SQL", "current", set()),
    "singlestore": ("mysql-family", "SingleStore SQL", "current", {"memsql"}),
    "solr": ("calcite-search", "Apache Solr SQL", "current", set()),
    "spark": ("spark-family", "Apache Spark SQL", "3+", {"sparksql"}),
    "spark2": ("spark-family", "Apache Spark SQL", "2.x", set()),
    "starrocks": ("mysql-family", "StarRocks SQL", "current", set()),
    "teradata": ("teradata", "Teradata SQL", "current", set()),
}

for _dialect_id, (
    _family,
    _engine,
    _version_selector,
    _aliases,
) in _BASELINE_SQLGLOT_DIALECTS.items():
    DEFAULT_DIALECTS[_dialect_id] = _genome(
        _dialect_id,
        _family,
        _engine,
        _version_selector,
        {"relational_select"},
        {SemanticDimension.RELATIONAL},
        _aliases,
        notes=(
            "Bootstrap SQLGlot parser coverage; dialect-specific capability coverage is partial.",
        ),
        coverage=_NATIVE_RELATIONAL_BASELINE,
    )


_KNOWN_UNPARSED_SQL_DIALECTS: dict[
    str,
    tuple[str, str, str, set[str]],
] = {
    "cockroachdb": ("postgres-family", "CockroachDB SQL", "current", {"cockroach"}),
    "db2": ("db2", "IBM Db2 SQL", "12.1.x", {"ibm-db2"}),
    "firebird": ("firebird", "Firebird SQL", "5.x", set()),
    "impala": ("hive-family", "Apache Impala SQL", "current", {"apache-impala"}),
    "sap_hana": ("sap-hana", "SAP HANA SQL", "2.0 SPS 08", {"hana"}),
    "tidb": ("mysql-family", "TiDB SQL", "8.x", set()),
    "vertica": ("vertica", "Vertica SQL", "26.2.x", set()),
    "yugabyte_ysql": (
        "postgres-family",
        "YugabyteDB YSQL",
        "2025.1+",
        {"ysql"},
    ),
    "flink": ("calcite-streaming", "Apache Flink SQL", "current", {"flink-sql"}),
    "ksqldb": ("streaming-sql", "ksqlDB SQL", "8.3+", {"ksql"}),
    "informix": ("informix", "IBM Informix SQL", "15.0.x", set()),
    "netezza": ("netezza", "IBM Netezza Performance Server SQL", "current", set()),
    "h2": ("h2", "H2 SQL", "2.x", set()),
    "pinot": ("calcite-analytics", "Apache Pinot SQL", "current", set()),
    "cratedb": ("postgres-family", "CrateDB SQL", "current", {"crate"}),
    "questdb": ("postgres-family", "QuestDB SQL", "current", set()),
}

for _dialect_id, (
    _family,
    _engine,
    _version_selector,
    _aliases,
) in _KNOWN_UNPARSED_SQL_DIALECTS.items():
    DEFAULT_DIALECTS[_dialect_id] = _genome(
        _dialect_id,
        _family,
        _engine,
        _version_selector,
        set(),
        set(),
        _aliases,
        notes=(
            "Known SQL dialect from official vendor documentation; parser, semantic, "
            "translation, and behavioral support are not yet established.",
        ),
    )


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
