"""Read-only operator evidence for an *existing* PostgreSQL target.

This module neither provisions infrastructure nor authorizes a consumer cutover.
All connection strings are supplied out of band and excluded from receipts.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from .receipts import canonical_digest, make_receipt


@dataclass(frozen=True, slots=True)
class TargetAdmissionExpectation:
    project_key: str
    target_key: str
    expected_provider_kind: str
    expected_provider_resource_ref: str
    expected_host: str
    expected_database: str
    expected_user: str
    expected_system_identifier: str
    expected_migration_version: str
    expected_migration_checksum: str
    expected_profile_digest: str
    expected_policy_digest: str
    project_scope: str = "PROJECT_LANTERN"
    expected_facade_id: str = "BT2_MATERIAL_CUT_V1"
    min_material_count: int = 1
    min_server_version_num: int = 160000


class _AdmissionFailure(Exception):
    def __init__(self, code: str, *, unknown: bool = False) -> None:
        self.code = code
        self.unknown = unknown
        super().__init__(code)


def _tls_configured(dsn: str, *, expected_host: str | None = None) -> bool:
    """Require explicit libpq verify-full and a real CA path, not PG* defaults."""
    try:
        params = conninfo_to_dict(dsn)
    except Exception:
        return False
    host = params.get("host", "")
    cert = params.get("sslrootcert", "")
    return (
        params.get("sslmode") == "verify-full"
        and bool(host)
        and "," not in host
        and (expected_host is None or host == expected_host)
        and bool(cert)
        and Path(cert).is_file()
    )


def _receipt(
    status: str, code: str, expectation: TargetAdmissionExpectation, checks: dict[str, str]
) -> dict[str, Any]:
    # Even non-secret registry references and physical IDs are suppressed; only
    # their digests remain for comparing an operator's pinned expectation.
    subject = {
        "status": status,
        "code": code,
        "checks": checks,
        "registry_subject_digest": canonical_digest(
            {
                "project_key": expectation.project_key,
                "target_key": expectation.target_key,
                "provider_kind": expectation.expected_provider_kind,
                "provider_resource_ref": expectation.expected_provider_resource_ref,
            }
        ),
        "expected_target_digest": canonical_digest(
            {
                "host": expectation.expected_host,
                "database": expectation.expected_database,
                "user": expectation.expected_user,
                "system_identifier": expectation.expected_system_identifier,
                "migration_version": expectation.expected_migration_version,
                "migration_checksum": expectation.expected_migration_checksum,
                "profile_digest": expectation.expected_profile_digest,
                "policy_digest": expectation.expected_policy_digest,
            }
        ),
        "evidence_ceiling": "OPERATOR_READONLY_TARGET_ADMISSION",
        "database_grants_qualified": False,
        "database_grants_state": "UNKNOWN",
        "facade_payload_qualified": False,
        "cutover_authorized": False,
    }
    return {
        "schema": "SQL_CONNECTOME_PG_TARGET_ADMISSION_V1",
        **subject,
        "receipt": make_receipt("PG_TARGET_ADMISSION", subject),
    }


def _expectations_complete(expected: TargetAdmissionExpectation) -> bool:
    required = (
        expected.project_key,
        expected.target_key,
        expected.expected_provider_kind,
        expected.expected_provider_resource_ref,
        expected.expected_host,
        expected.expected_database,
        expected.expected_user,
        expected.expected_system_identifier,
        expected.expected_migration_version,
        expected.expected_migration_checksum,
        expected.expected_profile_digest,
        expected.expected_policy_digest,
        expected.project_scope,
        expected.expected_facade_id,
    )
    return (
        all(isinstance(value, str) and value.strip() for value in required)
        and expected.expected_system_identifier.isdecimal()
        and expected.min_material_count >= 1
        and expected.min_server_version_num >= 160000
    )


def _check_registry(conn: Any, expected: TargetAdmissionExpectation) -> str:
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL search_path = pg_catalog, pg_temp")
        conn.execute("SET LOCAL statement_timeout = '5s'")
        registered = conn.execute(
            """
            SELECT p.project_key, p.updated_at AS project_updated_at,
                   t.target_key, t.target_id::text AS target_id,
                   t.updated_at AS target_updated_at, t.target_role, t.engine,
                   t.provider_kind, t.provider_resource_ref,
                   t.database_name, t.lifecycle_state
            FROM sql_connectome.projects p
            JOIN sql_connectome.database_targets t ON t.project_id = p.project_id
            WHERE p.project_key = %s AND t.target_key = %s
            """,
            (expected.project_key, expected.target_key),
        ).fetchone()
        if registered is None:
            raise _AdmissionFailure("REGISTRY_TARGET_MISSING")
        checks = {
            "project_key": expected.project_key,
            "target_key": expected.target_key,
            "target_role": "PRIMARY",
            "engine": "postgresql",
            "provider_kind": expected.expected_provider_kind,
            "provider_resource_ref": expected.expected_provider_resource_ref,
            "database_name": expected.expected_database,
            "lifecycle_state": "RUNNING",
        }
        if any(registered.get(key) != value for key, value in checks.items()):
            raise _AdmissionFailure("REGISTRY_TARGET_MISMATCH")
        return canonical_digest(dict(registered))


def _check_target(conn: Any, expected: TargetAdmissionExpectation) -> None:
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL search_path = pg_catalog, pg_temp")
        conn.execute("SET LOCAL statement_timeout = '5s'")
        ssl = conn.execute(
            "SELECT ssl FROM pg_catalog.pg_stat_ssl WHERE pid = pg_catalog.pg_backend_pid()"
        ).fetchone()
        if ssl is None or ssl.get("ssl") is not True:
            raise _AdmissionFailure("TARGET_TLS_NOT_ACTIVE")

        role = conn.execute(
            """
            SELECT rolname AS database_user, rolsuper, rolcreatedb, rolcreaterole,
                   rolreplication, rolbypassrls,
                   session_user AS session_user,
                   pg_catalog.pg_has_role(current_user, 'pg_read_all_data', 'USAGE')
                       AS has_read_all_data,
                   pg_catalog.pg_has_role(current_user, 'pg_read_all_data', 'SET')
                       AS can_set_read_all_data,
                   pg_catalog.pg_has_role(current_user, 'pg_write_all_data', 'USAGE')
                       AS has_write_all_data,
                   pg_catalog.pg_has_role(current_user, 'pg_write_all_data', 'SET')
                       AS can_set_write_all_data,
                   pg_catalog.pg_has_role(current_user, 'pg_read_server_files', 'USAGE')
                       AS has_read_server_files,
                   pg_catalog.pg_has_role(current_user, 'pg_read_server_files', 'SET')
                       AS can_set_read_server_files,
                   pg_catalog.pg_has_role(current_user, 'pg_write_server_files', 'USAGE')
                       AS has_write_server_files,
                   pg_catalog.pg_has_role(current_user, 'pg_write_server_files', 'SET')
                       AS can_set_write_server_files,
                   pg_catalog.pg_has_role(current_user, 'pg_execute_server_program', 'USAGE')
                       AS has_execute_server_program,
                   pg_catalog.pg_has_role(current_user, 'pg_execute_server_program', 'SET')
                       AS can_set_execute_server_program,
                   pg_catalog.pg_has_role(current_user, 'pg_monitor', 'USAGE')
                       AS has_monitor,
                   pg_catalog.pg_has_role(current_user, 'pg_monitor', 'SET')
                       AS can_set_monitor,
                   pg_catalog.pg_has_role(current_user, 'pg_signal_backend', 'USAGE')
                       AS has_signal_backend,
                   pg_catalog.pg_has_role(current_user, 'pg_signal_backend', 'SET')
                       AS can_set_signal_backend,
                   pg_catalog.pg_has_role(current_user, 'pg_checkpoint', 'USAGE')
                       AS has_checkpoint,
                   pg_catalog.pg_has_role(current_user, 'pg_checkpoint', 'SET')
                       AS can_set_checkpoint
            FROM pg_catalog.pg_roles WHERE rolname = current_user
            """
        ).fetchone()
        elevated = (
            "rolsuper",
            "rolcreatedb",
            "rolcreaterole",
            "rolreplication",
            "rolbypassrls",
            "has_read_all_data",
            "can_set_read_all_data",
            "has_write_all_data",
            "can_set_write_all_data",
            "has_read_server_files",
            "can_set_read_server_files",
            "has_write_server_files",
            "can_set_write_server_files",
            "has_execute_server_program",
            "can_set_execute_server_program",
            "has_monitor",
            "can_set_monitor",
            "has_signal_backend",
            "can_set_signal_backend",
            "has_checkpoint",
            "can_set_checkpoint",
        )
        if role is None or any(role.get(key) is not False for key in elevated):
            raise _AdmissionFailure("TARGET_ROLE_ELEVATED")
        if (
            role.get("database_user") != expected.expected_user
            or role.get("session_user") != expected.expected_user
        ):
            raise _AdmissionFailure("TARGET_IDENTITY_MISMATCH")

        observed = conn.execute(
            """
            SELECT pg_catalog.current_database() AS database_name,
                   current_user AS database_user,
                   pg_catalog.current_setting('server_version_num') AS server_version_num
            """
        ).fetchone()
        try:
            version = int(observed["server_version_num"]) if observed is not None else -1
        except (ValueError, TypeError, KeyError):
            version = -1
        if (
            observed is None
            or observed.get("database_name") != expected.expected_database
            or observed.get("database_user") != expected.expected_user
            or version < expected.min_server_version_num
        ):
            raise _AdmissionFailure("TARGET_IDENTITY_MISMATCH")

        migration = conn.execute(
            """
            SELECT version, checksum FROM sql_connectome.schema_migrations
            ORDER BY applied_at DESC, version DESC LIMIT 1
            """
        ).fetchone()
        if (
            migration is None
            or migration.get("version") != expected.expected_migration_version
            or migration.get("checksum") != expected.expected_migration_checksum
        ):
            raise _AdmissionFailure("TARGET_MIGRATION_MISMATCH")

        cut_rows = conn.execute(
            "SELECT * FROM bt2.material_cut_v1(%s)", (expected.project_scope,)
        ).fetchall()
        cut = cut_rows[0] if len(cut_rows) == 1 else None
        if (
            cut is None
            or cut.get("facade_id") != expected.expected_facade_id
            or cut.get("profile_digest") != expected.expected_profile_digest
            or cut.get("policy_digest") != expected.expected_policy_digest
            or not isinstance(cut.get("material_count"), int)
            or cut["material_count"] < expected.min_material_count
        ):
            raise _AdmissionFailure("TARGET_FACADE_MISMATCH")

        # The least-privileged role needs a separately granted EXECUTE right
        # on pg_control_system() to prove a physical cluster identifier. That
        # narrowly granted probe is a deployment prerequisite, not something
        # the CLI grants itself. Missing permission produces UNKNOWN.
        try:
            physical = conn.execute(
                "SELECT system_identifier::text FROM pg_catalog.pg_control_system()"
            ).fetchone()
        except Exception as exc:
            raise _AdmissionFailure("TARGET_CLUSTER_PROBE_UNAVAILABLE", unknown=True) from exc
        if physical is None or not physical.get("system_identifier"):
            raise _AdmissionFailure("TARGET_CLUSTER_PROBE_UNAVAILABLE", unknown=True)
        if str(physical["system_identifier"]) != expected.expected_system_identifier:
            raise _AdmissionFailure("TARGET_CLUSTER_MISMATCH")


def admit_postgres_target(
    registry_dsn: str,
    target_dsn: str,
    expectation: TargetAdmissionExpectation,
    *,
    connector: Callable[..., Any] = psycopg.connect,
) -> dict[str, Any]:
    """Read-only admission; no provider mutation, activation, or cutover effect."""
    checks: dict[str, str] = {}
    if not _expectations_complete(expectation):
        return _receipt("FAIL", "EXPECTATION_INCOMPLETE", expectation, checks)
    if not _tls_configured(registry_dsn):
        return _receipt("FAIL", "REGISTRY_TLS_CONFIG_UNSAFE", expectation, checks)
    if not _tls_configured(target_dsn, expected_host=expectation.expected_host):
        return _receipt("FAIL", "TARGET_TLS_CONFIG_UNSAFE", expectation, checks)
    checks["tls_configuration"] = "PASS"

    try:
        with connector(
            registry_dsn,
            autocommit=True,
            connect_timeout=5,
            row_factory=dict_row,
            application_name="sql-connectome-target-admission-registry",
        ) as registry:
            b0 = _check_registry(registry, expectation)
            checks["registry_b0"] = "PASS"
            with connector(
                target_dsn,
                autocommit=True,
                connect_timeout=5,
                row_factory=dict_row,
                application_name="sql-connectome-target-admission-target",
            ) as target:
                _check_target(target, expectation)
            try:
                b1 = _check_registry(registry, expectation)
            except _AdmissionFailure as exc:
                raise _AdmissionFailure("REGISTRY_BINDING_CHANGED", unknown=True) from exc
            if b0 != b1:
                raise _AdmissionFailure("REGISTRY_BINDING_CHANGED", unknown=True)
            checks["registry_b1"] = "PASS"
        checks["target_observation"] = "PASS"
    except _AdmissionFailure as exc:
        return _receipt("UNKNOWN" if exc.unknown else "FAIL", exc.code, expectation, checks)
    except Exception:
        # Driver/proxy/provider exceptions can contain raw DSNs or credentials.
        # Never echo their text or repr in a receipt or CLI output.
        return _receipt("UNKNOWN", "ADMISSION_PROBE_UNAVAILABLE", expectation, checks)
    return _receipt("PASS", "TARGET_ADMISSION_CHECKS_PASS", expectation, checks)
