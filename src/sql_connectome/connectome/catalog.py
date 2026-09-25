from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .model import DialectGenome, RewriteRule
from .registry import DEFAULT_DIALECTS, DEFAULT_REWRITE_RULES

DEFAULT_PARSER_ADAPTERS: dict[str, str] = {
    "athena": "athena",
    "bigquery": "bigquery",
    "clickhouse": "clickhouse",
    "databricks": "databricks",
    "doris": "doris",
    "dremio": "dremio",
    "drill": "drill",
    "druid": "druid",
    "duckdb": "duckdb",
    "dune": "dune",
    "exasol": "exasol",
    "fabric": "fabric",
    "hive": "hive",
    "materialize": "materialize",
    "mysql": "mysql",
    "oracle": "oracle",
    "postgresql": "postgres",
    "presto": "presto",
    "redshift": "redshift",
    "risingwave": "risingwave",
    "singlestore": "singlestore",
    "snowflake": "snowflake",
    "spark": "spark",
    "sqlite": "sqlite",
    "starrocks": "starrocks",
    "teradata": "teradata",
    "trino": "trino",
    "tsql": "tsql",
}


@dataclass(frozen=True, slots=True)
class ConnectomeCatalog:
    dialects: Mapping[str, DialectGenome]
    parser_adapters: Mapping[str, str]
    rewrite_rules: tuple[RewriteRule, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dialects",
            MappingProxyType(dict(self.dialects)),
        )
        object.__setattr__(
            self,
            "parser_adapters",
            MappingProxyType(dict(self.parser_adapters)),
        )
        object.__setattr__(self, "rewrite_rules", tuple(self.rewrite_rules))
        self._validate_aliases()

    def _validate_aliases(self) -> None:
        claims = {dialect_id: dialect_id for dialect_id in self.dialects}

        for dialect_id, genome in self.dialects.items():
            if genome.dialect_id != dialect_id:
                raise ValueError(
                    f"CATALOG_DIALECT_KEY_MISMATCH:{dialect_id}:{genome.dialect_id}"
                )

            for alias in genome.aliases:
                normalized = alias.strip().lower()
                owner = claims.get(normalized)
                if owner is not None and owner != dialect_id:
                    raise ValueError(f"CATALOG_ALIAS_COLLISION:{normalized}")
                claims[normalized] = dialect_id

    def resolve(self, dialect_id_or_alias: str) -> DialectGenome:
        key = dialect_id_or_alias.strip().lower()
        if key in self.dialects:
            return self.dialects[key]

        for genome in self.dialects.values():
            if key in genome.aliases:
                return genome

        raise KeyError(f"UNKNOWN_DIALECT:{dialect_id_or_alias}")

    def parser_adapter(self, dialect_id_or_alias: str) -> str:
        genome = self.resolve(dialect_id_or_alias)
        adapter = self.parser_adapters.get(genome.dialect_id)
        if not adapter:
            raise KeyError(f"PARSER_ADAPTER_NOT_CONFIGURED:{genome.dialect_id}")
        return adapter


DEFAULT_CATALOG = ConnectomeCatalog(
    dialects=DEFAULT_DIALECTS,
    parser_adapters=DEFAULT_PARSER_ADAPTERS,
    rewrite_rules=DEFAULT_REWRITE_RULES,
)
