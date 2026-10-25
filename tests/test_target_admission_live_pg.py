"""Disposable PostgreSQL 16 admission checks after exact BT2 V4 reconstruction.

The dedicated GitHub workflow creates the only database, login and TLS trust
anchor used here. This is not a provider, consumer or deployment qualification.
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import replace

import psycopg
import pytest
from ci_admission_guard import require_disposable_pg16_ci
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from sql_connectome.target_admission import (
    TargetAdmissionExpectation,
    admit_postgres_target,
)

pytestmark = pytest.mark.skipif(
    os.getenv("BT2_SQL_V4_EPHEMERAL_QUALIFICATION") != "1",
    reason="requires disposable PostgreSQL 16, pinned BT2 V4 and CI TLS",
)


@pytest.fixture(scope="module")
def admission_fixture() -> tuple[str, str, str, TargetAdmissionExpectation]:
    ca_path = require_disposable_pg16_ci(os.environ)
    admin_dsn = make_conninfo(
        os.environ["DATABASE_URL"],
        host="localhost",
        sslmode="verify-full",
        sslrootcert=str(ca_path),
    )
    login = "sql_admission_ci"
    password = secrets.token_urlsafe(30)

    with psycopg.connect(admin_dsn, autocommit=True, row_factory=dict_row) as admin:
        # Read-only server identity check before any fixture DDL or grants.
        version_row = admin.execute("SHOW server_version_num").fetchone()
        server_version = int(version_row["server_version_num"])
        if not 160000 <= server_version < 170000:
            raise RuntimeError("ADMISSION_FIXTURE_REQUIRES_POSTGRESQL_16")
        identity = admin.execute(
            "SELECT current_database() AS dbname, current_user AS username, "
            "inet_server_port() AS port"
        ).fetchone()
        if identity != {"dbname": "bt2_sql_ci", "username": "postgres", "port": 5432}:
            raise RuntimeError("ADMISSION_FIXTURE_WRONG_POSTGRESQL_SERVICE")
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}").format(
                sql.Identifier(login), sql.Literal(password)
            )
        )
        admin.execute("GRANT USAGE ON SCHEMA sql_connectome, bt2 TO sql_admission_ci")
        admin.execute(
            "GRANT SELECT ON ALL TABLES IN SCHEMA sql_connectome, bt2 TO sql_admission_ci"
        )
        admin.execute("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA bt2 TO sql_admission_ci")
        admin.execute(
            "GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO sql_admission_ci"
        )
        project_id = admin.execute(
            """INSERT INTO sql_connectome.projects(project_key, display_name)
               VALUES ('bt2', 'Disposable BT2 V4 test') RETURNING project_id"""
        ).fetchone()["project_id"]
        dbname = admin.execute("SELECT current_database() AS dbname").fetchone()["dbname"]
        admin.execute(
            """INSERT INTO sql_connectome.database_targets
                 (project_id, target_key, target_role, engine, provider_kind,
                  provider_resource_ref, database_name, lifecycle_state)
               VALUES (%s,'primary','PRIMARY','postgresql','ephemeral-pg16',
                       'disposable-ci-service',%s,'RUNNING')""",
            (project_id, dbname),
        )
        cut = admin.execute(
            "SELECT * FROM bt2.material_cut_v1('PROJECT_LANTERN')"
        ).fetchall()
        assert len(cut) == 1 and cut[0]["material_count"] == 2
        migration = admin.execute(
            """SELECT version, checksum FROM sql_connectome.schema_migrations
               ORDER BY applied_at DESC, version DESC LIMIT 1"""
        ).fetchone()
        cluster_id = admin.execute(
            "SELECT system_identifier::text FROM pg_catalog.pg_control_system()"
        ).fetchone()["system_identifier"]

    restricted_dsn = make_conninfo(admin_dsn, user=login, password=password)
    expectation = TargetAdmissionExpectation(
        project_key="bt2",
        target_key="primary",
        expected_provider_kind="ephemeral-pg16",
        expected_provider_resource_ref="disposable-ci-service",
        expected_host="localhost",
        expected_database=dbname,
        expected_user=login,
        expected_system_identifier=cluster_id,
        expected_migration_version=migration["version"],
        expected_migration_checksum=migration["checksum"],
        expected_profile_digest=cut[0]["profile_digest"],
        expected_policy_digest=cut[0]["policy_digest"],
        min_material_count=2,
    )
    return admin_dsn, restricted_dsn, password, expectation


def test_real_postgresql16_admission_pass_is_bounded_and_redacted(admission_fixture):
    _, restricted_dsn, password, expected = admission_fixture
    result = admit_postgres_target(restricted_dsn, restricted_dsn, expected)
    assert result["status"] == "PASS", result["code"]
    assert result["code"] == "TARGET_ADMISSION_CHECKS_PASS"
    assert result["checks"] == {
        "tls_configuration": "PASS",
        "registry_b0": "PASS",
        "registry_b1": "PASS",
        "target_observation": "PASS",
    }
    assert result["cutover_authorized"] is False
    assert result["database_grants_qualified"] is False
    assert result["facade_payload_qualified"] is False
    assert result["database_grants_state"] == "UNKNOWN"
    serialized = json.dumps(result, sort_keys=True)
    assert password not in serialized
    assert "disposable-ci-service" not in serialized


def test_real_postgresql16_denials_and_catalog_shadowing(admission_fixture):
    admin_dsn, restricted_dsn, _, expected = admission_fixture
    actual = admit_postgres_target(restricted_dsn, restricted_dsn, expected)
    assert actual["status"] == "PASS", actual["code"]

    bad_migration = replace(expected, expected_migration_checksum="WRONG")
    assert admit_postgres_target(restricted_dsn, restricted_dsn, bad_migration)["code"] == (
        "TARGET_MIGRATION_MISMATCH"
    )
    bad_facade = replace(expected, expected_facade_id="WRONG")
    assert admit_postgres_target(restricted_dsn, restricted_dsn, bad_facade)["code"] == (
        "TARGET_FACADE_MISMATCH"
    )
    privileged = admit_postgres_target(restricted_dsn, admin_dsn, expected)
    assert privileged["status"] == "FAIL"
    assert privileged["code"] == "TARGET_ROLE_ELEVATED"

    # With a real server, a hostile session search_path must not substitute a
    # similarly named function for pg_catalog.pg_control_system().
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute("CREATE SCHEMA admission_shadow")
        admin.execute(
            """CREATE FUNCTION admission_shadow.pg_control_system()
               RETURNS TABLE(system_identifier bigint)
               LANGUAGE SQL AS $$ SELECT 42::bigint $$"""
        )
        admin.execute("GRANT USAGE ON SCHEMA admission_shadow TO sql_admission_ci")
        admin.execute(
            "GRANT EXECUTE ON FUNCTION admission_shadow.pg_control_system()"
            " TO sql_admission_ci"
        )
    shadowed_dsn = make_conninfo(
        restricted_dsn, options="-c search_path=admission_shadow,pg_catalog"
    )
    result = admit_postgres_target(shadowed_dsn, shadowed_dsn, expected)
    assert result["status"] == "PASS", result["code"]

    with psycopg.connect(restricted_dsn, autocommit=True) as restricted:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            restricted.execute(
                "UPDATE sql_connectome.projects SET display_name = display_name"
            )
