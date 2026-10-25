"""Exercise SQL Connectome's opt-in gateway against a disposable BT2 database.

Only the dedicated workflow sets BT2_SQL_GATEWAY_EPHEMERAL_QUALIFICATION.
The gateway reader must authenticate independently over verified TLS and must
never receive direct protected BT2 table permissions or owner role membership.
"""

import asyncio
import os

import psycopg
import pytest
from mcp import Client

from sql_connectome.config import Settings
from sql_connectome.mcp_server import build_mcp_server

pytestmark = pytest.mark.skipif(
    os.getenv("BT2_SQL_GATEWAY_EPHEMERAL_QUALIFICATION") != "1",
    reason="requires disposable BT2 PostgreSQL gateway, reader LOGIN and TLS",
)


def test_restricted_tls_reader_gets_exact_bt2_cut_through_real_mcp():
    reader_dsn = os.environ["SQL_CONNECTOME_DATABASE_URL"]

    with psycopg.connect(reader_dsn, autocommit=True) as conn:
        identity = conn.execute(
            """SELECT current_user, session_user,
                      (SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()),
                      has_schema_privilege(current_user, 'bt2', 'USAGE'),
                      has_schema_privilege(current_user, 'sql_connectome', 'USAGE'),
                      pg_has_role(current_user, 'bt2_lantern_gateway_owner_v1', 'SET'),
                      has_function_privilege(
                          current_user, 'lantern_read.current_cut_v1()', 'EXECUTE'
                      )"""
        ).fetchone()
        assert identity == (
            "bt2_lantern_gateway_reader_v1",
            "bt2_lantern_gateway_reader_v1",
            True,
            False,
            False,
            False,
            True,
        )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT 1 FROM bt2.materials LIMIT 1")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SET ROLE bt2_lantern_gateway_owner_v1")

    settings = Settings(
        database_url=reader_dsn,
        api_token="disposable-mcp-test-only",
        lantern_route="gateway_v1",
    )

    async def check():
        server = build_mcp_server(settings, require_auth=False)
        async with Client(server) as client:
            cuts = []
            for _ in range(2):
                result = await client.call_tool(
                    "lantern_cut", {"project_scope": "PROJECT_LANTERN"}
                )
                assert result.is_error is False
                cut = result.structured_content
                assert cut is not None
                assert cut["schema"] == "SQL_CONNECTOME_LANTERN_CURRENT_CUT_V1"
                assert cut["runtime"]["database_user"] == (
                    "bt2_lantern_gateway_reader_v1"
                )
                assert cut["cut"]["facade_id"] == "BT2_MATERIAL_CUT_V1"
                assert cut["cut"]["material_count"] == len(cut["payload"]) == 2
                assert cut["receipt"]["kind"] == "LANTERN_CURRENT_CUT"
                assert [
                    [
                        row["material_id"],
                        row["canonical_digest"],
                        row["semantic_key"],
                        row["source_digest"],
                    ]
                    for row in cut["payload"]
                ] == cut["cut"]["exact_members"]
                assert all(
                    row["project_scope"] == "PROJECT_LANTERN"
                    and row["profile_digest"] == cut["cut"]["profile_digest"]
                    and row["policy_digest"] == cut["cut"]["policy_digest"]
                    for row in cut["payload"]
                )
                cuts.append(cut)

            assert cuts[0]["cut"] == cuts[1]["cut"]
            assert cuts[0]["payload"] == cuts[1]["payload"]
            denied = await client.call_tool(
                "lantern_cut", {"project_scope": "UNKNOWN_UNQUALIFIED_SCOPE"}
            )
            assert denied.is_error is True

    asyncio.run(check())
