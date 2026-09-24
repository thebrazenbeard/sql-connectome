from fastapi import Depends, FastAPI, HTTPException

from . import __version__
from .auth import require_bearer
from .config import Settings, get_settings
from .db import (
    lantern_current_cut,
    migration_status,
    platform_health,
    query_readonly,
    schema_inventory,
)
from .models import QueryRequest
from .sql_guard import SQLRejected

app = FastAPI(title="SQL Connectome", version=__version__)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/v1/platform/health", dependencies=[Depends(require_bearer)])
def get_platform_health(settings: Settings = Depends(get_settings)) -> dict:
    return platform_health(settings)


@app.get("/v1/schema", dependencies=[Depends(require_bearer)])
def get_schema(settings: Settings = Depends(get_settings)) -> dict:
    return schema_inventory(settings)


@app.post("/v1/query-readonly", dependencies=[Depends(require_bearer)])
def post_query_readonly(
    request: QueryRequest,
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        return query_readonly(settings, request.sql, request.params)
    except SQLRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/lantern/current-cut", dependencies=[Depends(require_bearer)])
def get_lantern_current_cut(
    project_scope: str = "PROJECT_LANTERN",
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        return lantern_current_cut(settings, project_scope)
    except RuntimeError as exc:
        if str(exc) == "LANTERN_CONTRACT_NOT_INSTALLED":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/migrations/status", dependencies=[Depends(require_bearer)])
def get_migration_status(settings: Settings = Depends(get_settings)) -> dict:
    return migration_status(settings)
