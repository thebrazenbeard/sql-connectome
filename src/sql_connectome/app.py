from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from . import __version__
from .auth import require_bearer
from .config import Settings, get_settings
from .connectome import (
    SQLTextError,
    bind_sql_text,
    inspect_sql_contracts,
    list_dialects,
    parse_sql_text,
    plan_translation,
    probe_sql_dialects,
    transpile_sql_text,
)
from .db import (
    lantern_current_cut,
    migration_status,
    platform_health,
    query_readonly,
    schema_inventory,
    validate_postgresql_readonly,
)
from .models import (
    DialectProbeRequest,
    PostgreSQLQualificationRequest,
    QueryRequest,
    SQLBindRequest,
    SQLParseRequest,
    SQLTranspileRequest,
    TranslationPlanRequest,
)
from .projects import ProjectRegistryError, list_projects, project_detail
from .qualification import qualify_translation_to_postgresql
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





@app.post("/v1/connectome/contracts", dependencies=[Depends(require_bearer)])
def post_connectome_contracts(request: SQLParseRequest) -> dict[str, object]:
    try:
        return inspect_sql_contracts(request.sql, request.dialect)
    except (KeyError, SQLTextError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/connectome/bind", dependencies=[Depends(require_bearer)])
def post_connectome_bind(request: SQLBindRequest) -> dict[str, object]:
    try:
        return bind_sql_text(
            request.sql,
            request.dialect,
            request.schema_context,
            database=request.database,
            catalog=request.catalog,
        )
    except (KeyError, SQLTextError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/connectome/probe", dependencies=[Depends(require_bearer)])
def post_connectome_probe(request: DialectProbeRequest) -> dict[str, object]:
    try:
        return probe_sql_dialects(request.sql, max_candidates=request.max_candidates)
    except SQLTextError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/connectome/parse", dependencies=[Depends(require_bearer)])
def post_connectome_parse(request: SQLParseRequest) -> dict[str, object]:
    try:
        return parse_sql_text(request.sql, request.dialect).as_dict()
    except (KeyError, SQLTextError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/connectome/transpile", dependencies=[Depends(require_bearer)])
def post_connectome_transpile(request: SQLTranspileRequest) -> dict[str, object]:
    try:
        return transpile_sql_text(
            request.sql,
            request.source_dialect,
            request.target_dialect,
            allow_lossy=request.allow_lossy,
        )
    except (KeyError, SQLTextError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc




@app.post(
    "/v1/connectome/qualify/postgresql",
    dependencies=[Depends(require_bearer)],
)
def post_connectome_qualify_postgresql(
    request: PostgreSQLQualificationRequest,
    settings: SettingsDep,
) -> dict[str, object]:
    try:
        return qualify_translation_to_postgresql(
            settings,
            request.sql,
            request.source_dialect,
            allow_lossy=request.allow_lossy,
        )
    except (KeyError, SQLTextError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/connectome/validate/postgresql", dependencies=[Depends(require_bearer)])
def post_connectome_validate_postgresql(
    request: QueryRequest,
    settings: SettingsDep,
) -> dict[str, object]:
    try:
        semantic = parse_sql_text(request.sql, "postgresql")
        engine = validate_postgresql_readonly(settings, request.sql, request.params)
        return {**engine, "semantic": semantic.as_dict()}
    except (SQLRejected, SQLTextError) as exc:
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


@app.get("/v1/projects", dependencies=[Depends(require_bearer)])
def get_projects(settings: SettingsDep) -> dict:
    return list_projects(settings)


@app.get("/v1/projects/{project_key}", dependencies=[Depends(require_bearer)])
def get_project(project_key: str, settings: SettingsDep) -> dict:
    try:
        return project_detail(settings, project_key)
    except ProjectRegistryError as exc:
        if str(exc) == "PROJECT_NOT_FOUND":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise


@app.get("/v1/migrations/status", dependencies=[Depends(require_bearer)])
def get_migration_status(settings: SettingsDep) -> dict:
    return migration_status(settings)
