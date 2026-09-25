from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SQL_CONNECTOME_", env_file=".env", extra="ignore")

    database_url: str
    api_token: SecretStr
    statement_timeout_ms: int = 5000
    max_rows: int = 500
    read_schemas: str = "bt2,public,sql_connectome"
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
