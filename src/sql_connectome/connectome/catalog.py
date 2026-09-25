from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .model import DialectGenome, RewriteRule
from .registry import DEFAULT_DIALECTS, DEFAULT_REWRITE_RULES


_DEFAULT_PARSER_ADAPTERS = {
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

DEFAULT_PARSER_ADAPTERS: Mapping[str, str] = MappingProxyType(
    dict(_DEFAULT_PARSER_ADAPTERS)
)


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
        self._validate()

    def _validate(self) -> None:
        claims = {dialect_id: dialect_id for dialect_id in self.dialects}

        for dialect_id, genome in self.dialects.items():
            normalized_id = dialect_id.strip().lower()
            if normalized_id != dialect_id:
                raise ValueError(f"CATALOG_DIALECT_KEY_NOT_NORMALIZED:{dialect_id}")
            if genome.dialect_id != dialect_id:
                raise ValueError(
                    f"CATALOG_DIALECT_KEY_MISMATCH:{dialect_id}:{genome.dialect_id}"
                )

            for alias in genome.aliases:
                normalized = alias.strip().lower()
                if not normalized:
                    raise ValueError(f"CATALOG_EMPTY_ALIAS:{dialect_id}")
                owner = claims.get(normalized)
                if owner is not None and owner != dialect_id:
                    raise ValueError(f"CATALOG_ALIAS_COLLISION:{normalized}")
                claims[normalized] = dialect_id

        for dialect_id, adapter in self.parser_adapters.items():
            if dialect_id not in self.dialects:
                raise ValueError(f"CATALOG_ORPHAN_PARSER_ADAPTER:{dialect_id}")
            if not adapter.strip():
                raise ValueError(f"CATALOG_EMPTY_PARSER_ADAPTER:{dialect_id}")

    def admit_dialect(
        self,
        genome: DialectGenome,
        *,
        parser_adapter: str,
    ) -> ConnectomeCatalog:
        dialects = dict(self.dialects)
        if genome.dialect_id in dialects:
            raise ValueError(f"CATALOG_DIALECT_ALREADY_ADMITTED:{genome.dialect_id}")
        dialects[genome.dialect_id] = genome

        parser_adapters = dict(self.parser_adapters)
        parser_adapters[genome.dialect_id] = parser_adapter

        return ConnectomeCatalog(
            dialects=dialects,
            parser_adapters=parser_adapters,
            rewrite_rules=self.rewrite_rules,
        )

    def resolve(self, dialect_id_or_alias: str) -> DialectGenome:
        key = dialect_id_or_alias.strip().lower()
        if key in self.dialects:
            return self.dialects[key]

        for genome in self.dialects.values():
            if key in {alias.strip().lower() for alias in genome.aliases}:
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
