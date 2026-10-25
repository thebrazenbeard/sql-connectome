import asyncio
import os

import pytest
from mcp import Client

from sql_connectome.config import Settings
from sql_connectome.mcp_server import StaticTokenVerifier, build_mcp_server

EXPECTED_TOOLS = {
    "platform_status",
    "compare_sql_dialects",
    "schema_catalog",
    "sql_dialects",
    "probe_sql_dialect",
    "parse_sql",
    "expression_contracts",
    "expression_registry",
    "expression_semantics",
    "bind_sql",
    "translation_plan",
    "transpile_sql",
    "type_graph",
    "validate_duckdb",
    "validate_sqlite",
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
            comparison = await client.call_tool(
                "compare_sql_dialects",
                {"source_dialect": "postgresql", "target_dialect": "sqlite"},
            )
            assert comparison.is_error is False
            assert comparison.structured_content is not None

            result = await client.call_tool(
                "parse_sql",
                {"sql": "SELECT 1 AS one", "dialect": "postgresql"},
            )
            assert result.is_error is False
            assert result.structured_content is not None

            contracts = await client.call_tool(
                "expression_contracts",
                {"sql": "SELECT COALESCE(NULL, 1)", "dialect": "postgresql"},
            )
            assert contracts.is_error is False
            assert contracts.structured_content is not None

            registry = await client.call_tool(
                "expression_registry",
                {},
            )
            assert registry.is_error is False
            assert registry.structured_content is not None

            semantic_inventory = await client.call_tool(
                "expression_semantics",
                {"sql": "SELECT COALESCE(NULL, 1)", "dialect": "postgresql"},
            )
            assert semantic_inventory.is_error is False
            assert semantic_inventory.structured_content is not None

            type_graph_result = await client.call_tool(
                "type_graph",
                {"dialect": "postgresql"},
            )
            assert type_graph_result.is_error is False
            assert type_graph_result.structured_content is not None

            duckdb_validation = await client.call_tool(
                "validate_duckdb",
                {
                    "sql": "SELECT id FROM users",
                    "schema_context": {"users": {"id": "INTEGER"}},
                },
            )
            assert duckdb_validation.is_error is False
            assert duckdb_validation.structured_content is not None

            sqlite_validation = await client.call_tool(
                "validate_sqlite",
                {
                    "sql": "SELECT id FROM users",
                    "schema_context": {"users": {"id": "INTEGER"}},
                },
            )
            assert sqlite_validation.is_error is False
            assert sqlite_validation.structured_content is not None

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


def test_static_bearer_cannot_run_adhoc_postgresql_mcp_tools_by_default(monkeypatch) -> None:
    from sql_connectome import mcp_server as mcp_module

    def forbidden(*args, **kwargs):
        raise AssertionError("Ad-hoc PostgreSQL tool reached the database")

    for function_name in (
        "query_readonly",
        "validate_postgresql_readonly",
        "qualify_translation_to_postgresql",
    ):
        monkeypatch.setattr(mcp_module, function_name, forbidden)

    async def scenario() -> None:
        server = build_mcp_server(make_settings(enable_adhoc_postgresql=False), require_auth=False)
        async with Client(server) as client:
            for name, arguments in (
                ("query_postgresql_readonly", {"sql": "SELECT * FROM private.secrets"}),
                ("validate_postgresql", {"sql": "SELECT * FROM private.secrets"}),
                (
                    "qualify_postgresql_translation",
                    {"sql": "SELECT * FROM private.secrets", "source_dialect": "postgresql"},
                ),
            ):
                result = await client.call_tool(name, arguments)
                assert result.is_error is True
                assert "ADHOC_POSTGRESQL_DISABLED" in str(result.content)

    asyncio.run(scenario())


def test_explicit_operator_opt_in_allows_mcp_adhoc_postgresql(monkeypatch) -> None:
    from sql_connectome import mcp_server as mcp_module

    monkeypatch.setattr(
        mcp_module,
        "query_readonly",
        lambda settings, sql, params=None: {"schema": "TEST_READ", "rows": [{"one": 1}]},
    )

    async def scenario() -> None:
        server = build_mcp_server(make_settings(enable_adhoc_postgresql=True), require_auth=False)
        async with Client(server) as client:
            result = await client.call_tool("query_postgresql_readonly", {"sql": "SELECT 1"})
            assert result.is_error is False
            assert result.structured_content is not None
            assert result.structured_content["rows"] == [{"one": 1}]

    asyncio.run(scenario())


@pytest.mark.skipif(
    not os.getenv("SQL_CONNECTOME_DATABASE_URL"),
    reason="SQL_CONNECTOME_DATABASE_URL not set",
)
def test_database_mcp_tool_roundtrip() -> None:
    async def scenario() -> None:
        server = build_mcp_server(
            make_settings(enable_adhoc_postgresql=True), require_auth=False
        )
        async with Client(server) as client:
            result = await client.call_tool(
                "query_postgresql_readonly",
                {"sql": "SELECT 1 AS one"},
            )
            assert result.is_error is False
            assert result.structured_content is not None

    asyncio.run(scenario())
