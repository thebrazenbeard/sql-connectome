from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from . import __version__
from .auth import require_bearer
from .config import Settings, get_settings
from .connectome import list_dialects, plan_translation
from .db import (
    lantern_current_cut,
    migration_status,
    platform_health,
    query_readonly,
    schema_inventory,
)
from .models import QueryRequest, TranslationPlanRequest
from .sql_guard import SQLRejected

app = FastAPI(title="SQL Connectome", version=__version__)
SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/v1/platform/health", dependencies=[Depends(require_bearer)])
def get_platform_health(settings: SettingsDep) -> dict:
    return platform_health(settings)


@app.get("/v1/schema", dependencies=[Depends(require_bearer)])
def get_schema(settings: SettingsDep) -> dict:
    return schema_inventory(settings)


@app.get("/v1/connectome/dialects", dependencies=[Depends(require_bearer)])
def get_connectome_dialects() -> dict[str, object]:
    dialects = list_dialects()
    return {"dialects": dialects, "count": len(dialects)}


@app.post("/v1/connectome/translation-plan", dependencies=[Depends(require_bearer)])
def post_connectome_translation_plan(request: TranslationPlanRequest) -> dict[str, object]:
    try:
        return plan_translation(
            request.source_dialect,
            request.target_dialect,
            request.required_capabilities,
        ).as_dict()
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/query-readonly", dependencies=[Depends(require_bearer)])
def post_query_readonly(request: QueryRequest, settings: SettingsDep) -> dict:
    try:
        return query_readonly(settings, request.sql, request.params)
    except SQLRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/lantern/current-cut", dependencies=[Depends(require_bearer)])
def get_lantern_current_cut(
    settings: SettingsDep,
    project_scope: str = "PROJECT_LANTERN",
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
def get_migration_status(settings: SettingsDep) -> dict:
    return migration_status(settings)
