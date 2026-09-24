from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50000)
    params: list[Any] | dict[str, Any] | None = None


class TranslationPlanRequest(BaseModel):
    source_dialect: str = Field(min_length=1, max_length=100)
    target_dialect: str = Field(min_length=1, max_length=100)
    required_capabilities: list[str] = Field(min_length=1, max_length=256)


class SQLParseRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50000)
    dialect: str = Field(min_length=1, max_length=100)


class SQLTranspileRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50000)
    source_dialect: str = Field(min_length=1, max_length=100)
    target_dialect: str = Field(min_length=1, max_length=100)
    allow_lossy: bool = False


class DialectProbeRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50000)
    max_candidates: int = Field(default=8, ge=1)


class SQLBindRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50000)
    dialect: str = Field(min_length=1, max_length=100)
    schema_context: dict[str, dict[str, str]]
    database: str | None = Field(default=None, max_length=256)
    catalog: str | None = Field(default=None, max_length=256)


class PostgreSQLQualificationRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50000)
    source_dialect: str = Field(min_length=1, max_length=100)
    allow_lossy: bool = False
