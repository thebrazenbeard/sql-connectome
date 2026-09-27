from __future__ import annotations

import hmac
from typing import Any

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AnyHttpUrl

from .config import Settings, get_settings
from .connectome import (
    SQLTextError,
    bind_sql_text,
    compare_dialects,
    inspect_sql_contracts,
    inspect_type_system,
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
from .duckdb_engine import validate_duckdb_readonly
from .qualification import qualify_translation_to_postgresql
from .sql_guard import SQLRejected
from .sqlite_engine import validate_sqlite_readonly

MAX_SQL_LENGTH = 50_000
MAX_CAPABILITIES = 256

SERVER_INSTRUCTIONS = """
SQL Connectome separates semantic understanding, translation, validation, execution, and
authorization. Never present translation or target-engine validation as proof of behavioral
equivalence. The exposed execution tools are read-only. No protected write tool exists in this
server. Preserve fidelity, currentness, provenance, and authority ceilings reported by tool results.
""".strip()


class StaticTokenVerifier(TokenVerifier):
    """Private-development verifier for an already-provisioned bearer token.

    Production deployments should replace this with verification against a real OAuth 2.1
    authorization server or token-introspection endpoint.
    """

    def __init__(self, token: str, *, resource: str, scope: str) -> None:
        self._token = token
        self._resource = resource
        self._scope = scope

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token, self._token):
            return None
        return AccessToken(
            token=token,
            client_id="sql-connectome-private",
            scopes=[self._scope],
            resource=self._resource,
            subject="private-operator",
        )


def _bounded_sql(sql: str) -> str:
    text = sql.strip()
    if not text:
        raise ToolError("SQL_EMPTY")
    if len(text) > MAX_SQL_LENGTH:
        raise ToolError("SQL_TOO_LARGE")
    return text


def _tool_error(exc: Exception) -> ToolError:
    return ToolError(str(exc) or type(exc).__name__)


def _build_auth(settings: Settings) -> tuple[StaticTokenVerifier, AuthSettings]:
    resource = settings.mcp_resource_url
    issuer = settings.mcp_issuer_url
    token = settings.mcp_static_token

    if not resource or not issuer or token is None:
        raise RuntimeError("MCP_AUTH_CONFIGURATION_INCOMPLETE")

    secret = token.get_secret_value()
    if not secret:
        raise RuntimeError("MCP_AUTH_TOKEN_EMPTY")

    verifier = StaticTokenVerifier(
        secret,
        resource=resource,
        scope=settings.mcp_required_scope,
    )
    auth = AuthSettings(
        issuer_url=AnyHttpUrl(issuer),
        resource_server_url=AnyHttpUrl(resource),
        required_scopes=[settings.mcp_required_scope],
        validate_token_resource=True,
    )
    return verifier, auth


def build_mcp_server(
    settings: Settings | None = None,
    *,
    require_auth: bool = True,
) -> MCPServer:
    """Build the SQL Connectome MCP server.

    In-memory tests may explicitly set require_auth=False. Network deployment should keep the
    default and provide complete resource-server settings.
    """

    resolved = settings or get_settings()
    kwargs: dict[str, Any] = {
        "instructions": SERVER_INSTRUCTIONS,
    }
    if require_auth:
        verifier, auth = _build_auth(resolved)
        kwargs["token_verifier"] = verifier
        kwargs["auth"] = auth

    mcp = MCPServer("SQL Connectome", **kwargs)

    @mcp.tool()
    def platform_status() -> dict[str, Any]:
        """Return exact PostgreSQL runtime identity, migration head, and a health receipt."""
        return platform_health(resolved)

    @mcp.tool()
    def schema_catalog() -> dict[str, Any]:
        """List governed database objects from the configured read-schema allowlist."""
        return schema_inventory(resolved)

    @mcp.tool()
    def sql_dialects() -> dict[str, Any]:
        """List admitted SQL dialect genomes and their current capability knowledge."""
        dialects = list_dialects()
        return {"dialects": dialects, "count": len(dialects)}

    @mcp.tool()
    def compare_sql_dialects(
        source_dialect: str,
        target_dialect: str,
    ) -> dict[str, Any]:
        """Compare admitted dialect evidence without claiming behavioral equivalence."""
        try:
            return compare_dialects(source_dialect, target_dialect)
        except (KeyError, ValueError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def type_graph(dialect: str) -> dict[str, Any]:
        """Inspect canonical type families and implicit-coercion evidence for one dialect."""
        try:
            return inspect_type_system(dialect)
        except (KeyError, SQLTextError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def probe_sql_dialect(sql: str, max_candidates: int = 8) -> dict[str, Any]:
        """Rank dialect candidates from parser/capability evidence without claiming identity."""
        statement = _bounded_sql(sql)
        if max_candidates < 1 or max_candidates > 32:
            raise ToolError("MAX_CANDIDATES_OUT_OF_RANGE")
        try:
            return probe_sql_dialects(statement, max_candidates=max_candidates)
        except SQLTextError as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def parse_sql(sql: str, dialect: str) -> dict[str, Any]:
        """Parse SQL into the semantic IR for a declared source dialect."""
        statement = _bounded_sql(sql)
        try:
            return parse_sql_text(statement, dialect).as_dict()
        except (KeyError, SQLTextError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def expression_contracts(sql: str, dialect: str) -> dict[str, Any]:
        """Inspect expression/function/operator/type contracts for a declared dialect."""
        statement = _bounded_sql(sql)
        try:
            return inspect_sql_contracts(statement, dialect)
        except (KeyError, SQLTextError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def bind_sql(
        sql: str,
        dialect: str,
        schema_context: dict[str, dict[str, str]],
        database: str | None = None,
        catalog: str | None = None,
    ) -> dict[str, Any]:
        """Bind identifiers/types against caller-supplied schema context.

        This performs static binding only and does not execute against an engine.
        """
        statement = _bounded_sql(sql)
        try:
            return bind_sql_text(
                statement,
                dialect,
                schema_context,
                database=database,
                catalog=catalog,
            )
        except (KeyError, SQLTextError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def translation_plan(
        source_dialect: str,
        target_dialect: str,
        required_capabilities: list[str],
    ) -> dict[str, Any]:
        """Plan dialect capability rewrites and report exact/constructive/lossy/unrepresentable."""
        if not required_capabilities or len(required_capabilities) > MAX_CAPABILITIES:
            raise ToolError("CAPABILITY_COUNT_OUT_OF_RANGE")
        try:
            return plan_translation(
                source_dialect,
                target_dialect,
                required_capabilities,
            ).as_dict()
        except (KeyError, ValueError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def transpile_sql(
        sql: str,
        source_dialect: str,
        target_dialect: str,
        allow_lossy: bool = False,
    ) -> dict[str, Any]:
        """Transpile with explicit fidelity gates; does not establish behavioral equivalence."""
        statement = _bounded_sql(sql)
        try:
            return transpile_sql_text(
                statement,
                source_dialect,
                target_dialect,
                allow_lossy=allow_lossy,
            )
        except (KeyError, SQLTextError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def validate_duckdb(
        sql: str,
        schema_context: dict[str, dict[str, str]] | None = None,
        params: list[Any] | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ask hardened in-memory DuckDB to EXPLAIN one SELECT without executing it."""
        statement = _bounded_sql(sql)
        try:
            semantic = parse_sql_text(statement, "duckdb")
            engine = validate_duckdb_readonly(
                statement,
                schema_context=schema_context,
                params=params,
            )
            return {**engine, "semantic": semantic.as_dict()}
        except (SQLRejected, SQLTextError, ValueError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def validate_sqlite(
        sql: str,
        schema_context: dict[str, dict[str, str]] | None = None,
        params: list[Any] | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ask hardened in-memory SQLite to plan one SELECT without executing it."""
        statement = _bounded_sql(sql)
        try:
            semantic = parse_sql_text(statement, "sqlite")
            engine = validate_sqlite_readonly(
                statement,
                schema_context=schema_context,
                params=params,
            )
            return {**engine, "semantic": semantic.as_dict()}
        except (SQLRejected, SQLTextError, ValueError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def validate_postgresql(
        sql: str,
        params: list[Any] | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ask PostgreSQL to EXPLAIN a single SELECT in a READ ONLY transaction; never ANALYZE."""
        statement = _bounded_sql(sql)
        try:
            semantic = parse_sql_text(statement, "postgresql")
            engine = validate_postgresql_readonly(resolved, statement, params)
            return {**engine, "semantic": semantic.as_dict()}
        except (SQLRejected, SQLTextError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def qualify_postgresql_translation(
        sql: str,
        source_dialect: str,
        allow_lossy: bool = False,
    ) -> dict[str, Any]:
        """Translate to PostgreSQL then qualify the generated SQL by read-only EXPLAIN."""
        statement = _bounded_sql(sql)
        try:
            return qualify_translation_to_postgresql(
                resolved,
                statement,
                source_dialect,
                allow_lossy=allow_lossy,
            )
        except (KeyError, SQLTextError) as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def query_postgresql_readonly(
        sql: str,
        params: list[Any] | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute one SELECT in a PostgreSQL READ ONLY transaction with timeout and row cap."""
        statement = _bounded_sql(sql)
        try:
            return query_readonly(resolved, statement, params)
        except SQLRejected as exc:
            raise _tool_error(exc) from exc

    @mcp.tool()
    def migration_state() -> dict[str, Any]:
        """Return the applied migration ledger and exact runtime identity without mutating it."""
        return migration_status(resolved)

    @mcp.tool()
    def lantern_cut(project_scope: str = "PROJECT_LANTERN") -> dict[str, Any]:
        """Read one Lantern cut and payload from a REPEATABLE READ READ ONLY snapshot."""
        if not project_scope or len(project_scope) > 256:
            raise ToolError("PROJECT_SCOPE_INVALID")
        try:
            return lantern_current_cut(resolved, project_scope)
        except (RuntimeError, ValueError) as exc:
            raise _tool_error(exc) from exc

    return mcp


def main() -> None:
    """Run the authenticated Streamable HTTP MCP resource server."""

    settings = get_settings()
    mcp = build_mcp_server(settings, require_auth=True)
    mcp.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()
