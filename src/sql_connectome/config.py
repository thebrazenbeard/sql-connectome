from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SQL_CONNECTOME_",
        env_file=".env",
        extra="ignore",
        validate_assignment=True,
    )

    database_url: str
    api_token: SecretStr
    # PostgreSQL treats statement_timeout=0 as unlimited. Fail closed on
    # operator typos, including malformed env values and post-init assignments.
    statement_timeout_ms: int = Field(default=5000, ge=1, le=60_000)
    max_rows: int = Field(default=500, ge=1, le=10_000)
    read_schemas: str = "bt2,public,sql_connectome"
    # The private static bearer is not a tenant principal. Explicit operator opt-in
    # is required before it can submit live PostgreSQL SQL for execution/planning.
    enable_adhoc_postgresql: bool = False
    # The least-privilege gateway is deliberately opt-in until its PostgreSQL
    # role grants, runtime endpoint, and independent consumer are qualified.
    lantern_route: Literal["legacy_v4", "gateway_v1"] = "legacy_v4"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8001
    mcp_resource_url: str | None = None
    mcp_issuer_url: str | None = None
    mcp_static_token: SecretStr | None = None
    mcp_required_scope: str = "sql-connectome:read"

    @property
    def schema_allowlist(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.read_schemas.split(",") if part.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
