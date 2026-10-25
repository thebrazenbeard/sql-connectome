"""Transport-independent fail-closed checks for the static-service bearer boundary."""

import pytest
from fastapi import HTTPException
from mcp.server.mcpserver.exceptions import ToolError

from sql_connectome import app as rest_module
from sql_connectome import mcp_server as mcp_module
from sql_connectome.config import Settings
from sql_connectome.models import (
    PostgreSQLQualificationRequest,
    QueryRequest,
)


def _settings(enabled: bool = False) -> Settings:
    return Settings(
        database_url="postgresql://unused:unused@localhost/unused",
        api_token="shared-static-test-token",
        enable_adhoc_postgresql=enabled,
        read_schemas="public",
    )


@pytest.mark.parametrize(
    ("handler", "payload", "callee"),
    [
        (
            rest_module.post_query_readonly,
            QueryRequest(sql="SELECT * FROM private.secrets"),
            "query_readonly",
        ),
        (
            rest_module.post_connectome_validate_postgresql,
            QueryRequest(sql="SELECT * FROM private.secrets"),
            "validate_postgresql_readonly",
        ),
        (
            rest_module.post_connectome_qualify_postgresql,
            PostgreSQLQualificationRequest(
                sql="SELECT * FROM private.secrets", source_dialect="postgresql"
            ),
            "qualify_translation_to_postgresql",
        ),
    ],
)
def test_static_bearer_is_insufficient_for_rest_live_sql(
    monkeypatch, handler, payload, callee
) -> None:
    def would_leak(*args, **kwargs):
        raise AssertionError("Executed query despite disabled ad-hoc SQL")

    monkeypatch.setattr(rest_module, callee, would_leak)
    with pytest.raises(HTTPException) as raised:
        handler(payload, _settings())
    assert raised.value.status_code == 403
    assert raised.value.detail == "ADHOC_POSTGRESQL_DISABLED"


@pytest.mark.parametrize(
    ("tool_name", "arguments", "callee"),
    [
        ("query_postgresql_readonly", {"sql": "SELECT * FROM private.secrets"}, "query_readonly"),
        (
            "validate_postgresql",
            {"sql": "SELECT * FROM private.secrets"},
            "validate_postgresql_readonly",
        ),
        (
            "qualify_postgresql_translation",
            {"sql": "SELECT * FROM private.secrets", "source_dialect": "postgresql"},
            "qualify_translation_to_postgresql",
        ),
    ],
)
def test_static_bearer_is_insufficient_for_mcp_live_sql(
    monkeypatch, tool_name, arguments, callee
) -> None:
    def would_leak(*args, **kwargs):
        raise AssertionError("Executed query despite disabled ad-hoc SQL")

    monkeypatch.setattr(mcp_module, callee, would_leak)
    server = mcp_module.build_mcp_server(_settings(), require_auth=False)
    with pytest.raises(ToolError, match="ADHOC_POSTGRESQL_DISABLED"):
        server._tool_manager._tools[tool_name].fn(**arguments)


def test_explicit_private_operator_opt_in_for_rest_and_mcp(monkeypatch) -> None:
    settings = _settings(enabled=True)
    monkeypatch.setattr(
        rest_module, "query_readonly", lambda *args, **kwargs: {"rows": [{"one": 1}]}
    )
    monkeypatch.setattr(
        mcp_module, "query_readonly", lambda *args, **kwargs: {"rows": [{"one": 1}]}
    )
    assert rest_module.post_query_readonly(QueryRequest(sql="SELECT 1"), settings) == {
        "rows": [{"one": 1}]
    }
    server = mcp_module.build_mcp_server(settings, require_auth=False)
    assert server._tool_manager._tools["query_postgresql_readonly"].fn(sql="SELECT 1") == {
        "rows": [{"one": 1}]
    }
