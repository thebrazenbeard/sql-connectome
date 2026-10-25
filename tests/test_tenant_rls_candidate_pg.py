"""Real PostgreSQL RLS falsifiers on a disposable CI database only."""

from __future__ import annotations

import os
import secrets
from urllib.parse import urlsplit

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from test_tenant_rls_candidate import AUDIENCE, ISSUER, TENANT_A, _claims

from sql_connectome.tenant_rls_candidate import authorize_principal, read_tenant_documents

TENANT_B = "22222222-2222-4222-8222-222222222222"
CI_READER = "sql_connectome_rls_ci_reader"
CI_SCHEMA = "sql_connectome_rls_ci"


@pytest.mark.skipif(
    os.getenv("SQL_CONNECTOME_TENANT_RLS_CI_EPHEMERAL") != "1",
    reason="requires explicitly admitted disposable PostgreSQL CI service",
)
def test_real_rls_principals_and_pooled_transaction_recovery():
    admin_dsn = os.environ["SQL_CONNECTOME_DATABASE_URL"]
    parsed = urlsplit(admin_dsn)
    if parsed.hostname not in {"localhost", "127.0.0.1"} or parsed.path != "/sql_connectome":
        pytest.fail("TENANT_RLS_CI_REQUIRES_PINNED_LOOPBACK_DATABASE")

    password = secrets.token_hex(24)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        if admin.execute("SELECT to_regnamespace(%s)", (CI_SCHEMA,)).fetchone()[0]:
            pytest.fail("TENANT_RLS_CI_SCHEMA_ALREADY_EXISTS")
        if admin.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (CI_READER,)).fetchone():
            pytest.fail("TENANT_RLS_CI_ROLE_ALREADY_EXISTS")

        created = False
        try:
            admin.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOINHERIT NOBYPASSRLS NOSUPERUSER PASSWORD {}"
                ).format(
                    sql.Identifier(CI_READER), sql.Literal(password)
                )
            )
            created = True
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(CI_SCHEMA)))
            admin.execute(
                """
                CREATE TABLE sql_connectome_rls_ci.tenant_documents (
                  document_id integer PRIMARY KEY, tenant_id uuid NOT NULL, body text NOT NULL
                )
                """
            )
            admin.execute(
                "INSERT INTO sql_connectome_rls_ci.tenant_documents VALUES "
                "(1, %s, 'A-1'), (2, %s, 'B-1'), (3, %s, 'A-2')",
                (TENANT_A, TENANT_B, TENANT_A),
            )
            admin.execute(
                "ALTER TABLE sql_connectome_rls_ci.tenant_documents ENABLE ROW LEVEL SECURITY"
            )
            admin.execute(
                "ALTER TABLE sql_connectome_rls_ci.tenant_documents FORCE ROW LEVEL SECURITY"
            )
            admin.execute(
                """
                CREATE POLICY tenant_only ON sql_connectome_rls_ci.tenant_documents
                FOR SELECT USING (
                  tenant_id = nullif(current_setting('sql_connectome.tenant_id', true), '')::uuid
                )
                """
            )
            admin.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(CI_SCHEMA), sql.Identifier(CI_READER)))
            admin.execute(sql.SQL("GRANT SELECT ON {}.tenant_documents TO {}").format(
                sql.Identifier(CI_SCHEMA), sql.Identifier(CI_READER)))

            reader_dsn = make_conninfo(
                admin_dsn,
                user=CI_READER,
                password=password,
                application_name="sql-connectome-tenant-rls-ci",
            )
            with psycopg.connect(reader_dsn, autocommit=True, row_factory=dict_row) as reader:
                # With no trusted tenant binding, RLS must expose nothing.
                assert reader.execute(
                    "SELECT document_id FROM sql_connectome_rls_ci.tenant_documents"
                ).fetchall() == []

                # Threat-model falsifier: a caller holding this DB login and
                # arbitrary SQL *can spoof* the custom GUC, defeating RLS.
                # Such access must NEVER be provided by a public tenant API.
                reader.execute(
                    "SELECT set_config('sql_connectome.tenant_id', %s, false)",
                    (TENANT_B,),
                )
                assert [row["body"] for row in reader.execute(
                    "SELECT body FROM sql_connectome_rls_ci.tenant_documents"
                ).fetchall()] == ["B-1"]
                reader.execute("RESET sql_connectome.tenant_id")
                assert reader.execute(
                    "SELECT document_id FROM sql_connectome_rls_ci.tenant_documents"
                ).fetchall() == []

                def fixture_verifier(token: str) -> dict:
                    if token not in {"signed-a", "signed-b"}:
                        raise ValueError("forged")
                    return _claims(
                        tenant_id=TENANT_A if token == "signed-a" else TENANT_B,
                        nbf=1,
                        exp=4102444800,
                    )

                def principal(token: str):
                    return authorize_principal(
                        token, fixture_verifier,
                        expected_issuer=ISSUER, expected_audience=AUDIENCE, now=1100,
                    )

                def read(token: str):
                    return read_tenant_documents(
                        reader, token, fixture_verifier,
                        expected_issuer=ISSUER, expected_audience=AUDIENCE,
                        enabled=True,
                    )

                assert str(principal("signed-a").tenant_id) == TENANT_A
                assert [row["body"] for row in read("signed-a")] == [
                    "A-1", "A-2"
                ]
                assert [row["body"] for row in read("signed-b")] == [
                    "B-1"
                ]
                assert [row["body"] for row in read("signed-a")] == [
                    "A-1", "A-2"
                ]
                assert reader.execute(
                    "SELECT document_id FROM sql_connectome_rls_ci.tenant_documents"
                ).fetchall() == []

                # PostgreSQL permissive RLS policies OR together. A drifted
                # USING(true) policy must fail the consumer's exact tenant
                # post-read binding; do not silently filter the other tenant.
                admin.execute(
                    "CREATE POLICY accidental_overread ON "
                    "sql_connectome_rls_ci.tenant_documents FOR SELECT USING (true)"
                )
                try:
                    with pytest.raises(PermissionError, match="TENANT_RLS_POLICY_DRIFT"):
                        read("signed-a")
                finally:
                    admin.execute(
                        "DROP POLICY accidental_overread ON "
                        "sql_connectome_rls_ci.tenant_documents"
                    )
                assert [row["body"] for row in read("signed-a")] == ["A-1", "A-2"]

                # Even ADMIN-only, SET-false membership is not admitted:
                # it could be used to regrant SET privileges in PostgreSQL 17.
                admin.execute("CREATE ROLE sql_connectome_rls_ci_extra NOLOGIN")
                admin.execute(
                    f"GRANT sql_connectome_rls_ci_extra TO {CI_READER} "
                    "WITH ADMIN TRUE, SET FALSE, INHERIT FALSE"
                )
                try:
                    with pytest.raises(PermissionError, match="TENANT_RLS_ROLE_NOT_ISOLATED"):
                        read("signed-a")
                finally:
                    admin.execute(f"REVOKE sql_connectome_rls_ci_extra FROM {CI_READER}")
                    admin.execute("DROP ROLE sql_connectome_rls_ci_extra")
                admin.execute(sql.SQL("ALTER ROLE {} CREATEROLE").format(sql.Identifier(CI_READER)))
                try:
                    with pytest.raises(PermissionError, match="TENANT_RLS_ROLE_NOT_ISOLATED"):
                        read("signed-a")
                finally:
                    admin.execute(sql.SQL("ALTER ROLE {} NOCREATEROLE").format(
                        sql.Identifier(CI_READER)))
                admin.execute(sql.SQL("ALTER ROLE {} BYPASSRLS").format(
                    sql.Identifier(CI_READER)))
                try:
                    with pytest.raises(PermissionError, match="TENANT_RLS_ROLE_NOT_ISOLATED"):
                        read("signed-a")
                finally:
                    admin.execute(sql.SQL("ALTER ROLE {} NOBYPASSRLS").format(
                        sql.Identifier(CI_READER)))

                # Error after transaction-local scope binding must roll back.
                admin.execute(sql.SQL("REVOKE SELECT ON {}.tenant_documents FROM {}").format(
                    sql.Identifier(CI_SCHEMA), sql.Identifier(CI_READER)))
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    read("signed-b")
                admin.execute(sql.SQL("GRANT SELECT ON {}.tenant_documents TO {}").format(
                    sql.Identifier(CI_SCHEMA), sql.Identifier(CI_READER)))
                assert [row["body"] for row in read("signed-a")] == [
                    "A-1", "A-2"
                ]

                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    reader.execute("SET ROLE postgres")
        finally:
            if created:
                admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(CI_SCHEMA)))
                admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(CI_READER)))
