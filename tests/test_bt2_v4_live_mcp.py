"""Pin-and-rebuild BT2 PostgreSQL V4 through the real SQL Connectome MCP client.

The dedicated CI workflow sets BT2_SQL_V4_EPHEMERAL_QUALIFICATION=1 after
reconstructing a disposable PostgreSQL 16 database from a pinned BT2 source.
This does not qualify any host provider or Project Lantern installation.
"""

import asyncio
import os

import pytest
from mcp import Client

from sql_connectome.config import Settings
from sql_connectome.mcp_server import build_mcp_server

pytestmark = pytest.mark.skipif(
    os.getenv("BT2_SQL_V4_EPHEMERAL_QUALIFICATION") != "1",
    reason="requires pinned BT2 blank rebuild in isolated PostgreSQL 16",
)


def _assert_v4_lantern_cut(data):
    assert data["schema"] == "SQL_CONNECTOME_LANTERN_CURRENT_CUT_V1"
    assert data["runtime"]["identity_digest"]
    assert data["runtime"]["migration_head"]["version"] == "0002"
    cut = data["cut"]
    payload = data["payload"]
    assert cut["facade_id"] == "BT2_MATERIAL_CUT_V1"
    assert cut["material_count"] == len(payload) == 2
    assert cut["profile_digest"] and cut["policy_digest"]
    actual_members = [
        [
            row["material_id"],
            row["canonical_digest"],
            row["semantic_key"],
            row["source_digest"],
        ]
        for row in payload
    ]
    assert actual_members == cut["exact_members"]
    assert all(row["project_scope"] == "PROJECT_LANTERN" for row in payload)
    assert all(row["profile_digest"] == cut["profile_digest"] for row in payload)
    assert all(row["policy_digest"] == cut["policy_digest"] for row in payload)
    assert data["receipt"]["kind"] == "LANTERN_CURRENT_CUT"
    assert data["receipt"]["subject"]["facade_id"] == "BT2_MATERIAL_CUT_V1"


def test_real_mcp_lantern_cut_against_pinned_bt2_rebuild():
    database_url = os.environ["SQL_CONNECTOME_DATABASE_URL"]
    settings = Settings(database_url=database_url, api_token="ephemeral-ci-only")

    async def check():
        server = build_mcp_server(settings, require_auth=False)
        async with Client(server) as client:
            reads = []
            for _ in range(2):
                result = await client.call_tool(
                    "lantern_cut", {"project_scope": "PROJECT_LANTERN"}
                )
                assert result.is_error is False
                assert result.structured_content is not None
                _assert_v4_lantern_cut(result.structured_content)
                reads.append(result.structured_content)

            assert reads[0]["cut"] == reads[1]["cut"]
            assert reads[0]["payload"] == reads[1]["payload"]
            assert reads[0]["receipt"]["subject"] == reads[1]["receipt"]["subject"]

            missing = await client.call_tool(
                "lantern_cut", {"project_scope": "UNKNOWN_UNQUALIFIED_SCOPE"}
            )
            assert missing.is_error is True

    asyncio.run(check())
