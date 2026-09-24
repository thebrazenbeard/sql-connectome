from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=50000)
    params: list[Any] | dict[str, Any] | None = None
