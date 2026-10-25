"""Exercise the actual loopback Streamable HTTP authentication boundary.

The process uses only fixture credentials and semantic (non-DB) MCP tools.
No PostgreSQL service, grant, migration, or existing MCP listener is touched.
"""

import asyncio
import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import contextmanager

import httpx
import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

_SERVER_CODE = """
import os
import sys

from sql_connectome.config import Settings
from sql_connectome.mcp_server import StaticTokenVerifier, build_mcp_server

port = int(sys.argv[1])
claim_variant = sys.argv[2]
resource = f"http://127.0.0.1:{port}/mcp"
settings = Settings(
    database_url="postgresql://fixture:fixture@127.0.0.1:1/not-used",
    api_token="fixture-rest-token",
    mcp_resource_url=resource,
    mcp_issuer_url=f"http://127.0.0.1:{port}/fixture-issuer",
    mcp_static_token=os.environ["SQL_CONNECTOME_NETWORK_AUTH_TEST_TOKEN"],
    mcp_required_scope="sql-connectome:read",
)
if claim_variant != "normal":
    original = StaticTokenVerifier.verify_token

    async def altered_claims(self, presented_token):
        accepted = await original(self, presented_token)
        if accepted is None:
            return None
        if claim_variant == "wrong_scope":
            return accepted.model_copy(update={"scopes": ["other:scope"]})
        if claim_variant == "wrong_resource":
            return accepted.model_copy(update={"resource": resource + "/other"})
        raise AssertionError(f"Unexpected claim variant: {claim_variant}")

    StaticTokenVerifier.verify_token = altered_claims

server = build_mcp_server(settings, require_auth=True)
server.run(
    transport="streamable-http",
    host="127.0.0.1",
    port=port,
    stateless_http=True,
    json_response=True,
)
"""


@contextmanager
def _loopback_mcp(claim_variant: str = "normal"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]

    token = secrets.token_urlsafe(32)
    environment = os.environ.copy()
    environment["SQL_CONNECTOME_NETWORK_AUTH_TEST_TOKEN"] = token
    process = subprocess.Popen(
        [sys.executable, "-c", _SERVER_CODE, str(port), claim_variant],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=environment,
    )
    try:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"Fixture MCP server exited: {process.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError("Fixture MCP server failed to listen on loopback")
        yield f"http://127.0.0.1:{port}/mcp", token
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stderr:
            process.stderr.close()


_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "sql-connectome-network-auth-test", "version": "1"},
    },
}


@pytest.mark.parametrize("provided_token", [None, "definitely-not-the-token"])
def test_network_mcp_rejects_missing_or_invalid_bearer(provided_token: str | None) -> None:
    with _loopback_mcp() as (url, _token):
        headers = {"Accept": "application/json, text/event-stream"}
        if provided_token is not None:
            headers["Authorization"] = f"Bearer {provided_token}"
        response = httpx.post(url, json=_INITIALIZE, headers=headers, timeout=10)
        assert response.status_code == 401


def test_valid_bearer_reaches_real_network_mcp_semantic_tool() -> None:
    with _loopback_mcp() as (url, token):

        async def scenario() -> None:
            async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as http:
                async with Client(streamable_http_client(url, http_client=http)) as client:
                    result = await client.call_tool("sql_dialects", {})
                    assert result.is_error is False
                    assert result.structured_content is not None
                    assert result.structured_content["count"] > 0

        asyncio.run(scenario())


@pytest.mark.parametrize("claim_variant", ["wrong_scope", "wrong_resource"])
def test_network_mcp_rejects_unauthorized_scope_or_resource(claim_variant: str) -> None:
    # The built-in static-token verifier always emits the configured scope and
    # resource. Vary *only* the returned claims inside this disposable process
    # to exercise the real network resource-server enforcement.
    with _loopback_mcp(claim_variant) as (url, token):
        response = httpx.post(
            url,
            json=_INITIALIZE,
            headers={
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
        assert response.status_code in {401, 403}
