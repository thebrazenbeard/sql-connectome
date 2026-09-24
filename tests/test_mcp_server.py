import asyncio
import os

import pytest
from mcp import Client

from sql_connectome.config import Settings
from sql_connectome.mcp_server import StaticTokenVerifier, build_mcp_server

EXPECTED_TOOLS = {
    "platform_status",
    "schema_catalog",
    "sql_dialects",
    "probe_sql_dialect",
    "parse_sql",
    "bind_sql",
    "translation_plan",
    "transpile_sql",
    "validate_postgresql",
    "qualify_postgresql_translation",
    "query_postgresql_readonly",
    "migration_state",
    "lantern_cut",
}


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": os.getenv(
            "SQL_CONNECTOME_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/sql_connectome",
        ),
        "api_token": "api-test-token",
    }
    values.update(overrides)
    return Settings(**values)


def test_mcp_tool_surface_is_read_only_and_explicit() -> None:
    async def scenario() -> None:
        server = build_mcp_server(make_settings(), require_auth=False)
        async with Client(server) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == EXPECTED_TOOLS
            assert not any(
                token in name
                for name in names
                for token in ("write", "delete", "drop", "apply_migration", "restore")
            )

    asyncio.run(scenario())


def test_semantic_mcp_tool_roundtrip() -> None:
    async def scenario() -> None:
        server = build_mcp_server(make_settings(), require_auth=False)
        async with Client(server) as client:
            result = await client.call_tool(
                "parse_sql",
                {"sql": "SELECT 1 AS one", "dialect": "postgresql"},
            )
            assert result.is_error is False
            assert result.structured_content is not None

    asyncio.run(scenario())


def test_mcp_auth_configuration_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="MCP_AUTH_CONFIGURATION_INCOMPLETE"):
        build_mcp_server(make_settings(), require_auth=True)


def test_static_token_verifier_accepts_only_exact_token() -> None:
    async def scenario() -> None:
        verifier = StaticTokenVerifier(
            "expected-token",
            resource="https://sql-connectome.example.test/mcp",
            scope="sql-connectome:read",
        )
        accepted = await verifier.verify_token("expected-token")
        rejected = await verifier.verify_token("wrong-token")

        assert accepted is not None
        assert accepted.client_id == "sql-connectome-private"
        assert accepted.scopes == ["sql-connectome:read"]
        assert rejected is None

    asyncio.run(scenario())


@pytest.mark.skipif(
    not os.getenv("SQL_CONNECTOME_DATABASE_URL"),
    reason="SQL_CONNECTOME_DATABASE_URL not set",
)
def test_database_mcp_tool_roundtrip() -> None:
    async def scenario() -> None:
        server = build_mcp_server(make_settings(), require_auth=False)
        async with Client(server) as client:
            result = await client.call_tool(
                "query_postgresql_readonly",
                {"sql": "SELECT 1 AS one"},
            )
            assert result.is_error is False
            assert result.structured_content is not None

    asyncio.run(scenario())
