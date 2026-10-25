"""Inert admission tests: no real PostgreSQL connections or provider effects."""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path

import pytest

from sql_connectome.target_admission import TargetAdmissionExpectation, admit_postgres_target


class FakeConnection:
    def __init__(
        self,
        rows: dict[str, object],
        after_physical_probe: Callable[[], None] | None = None,
    ) -> None:
        self.rows = rows
        self.queries: list[str] = []
        self.after_physical_probe = after_physical_probe

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def transaction(self) -> nullcontext[None]:
        return nullcontext()

    def execute(self, sql: str, params: object = ()) -> FakeCursor:
        self.queries.append(sql)
        if "SET TRANSACTION" in sql or "SET LOCAL" in sql:
            return FakeCursor(None)
        if "FROM sql_connectome.projects" in sql:
            return FakeCursor(self.rows["registry"])
        if "FROM pg_catalog.pg_stat_ssl" in sql:
            return FakeCursor(self.rows["ssl"])
        if "FROM pg_catalog.pg_roles" in sql:
            return FakeCursor(self.rows["role"])
        if "current_database()" in sql:
            return FakeCursor(self.rows["identity"])
        if "FROM sql_connectome.schema_migrations" in sql:
            return FakeCursor(self.rows["migration"])
        if "FROM bt2.material_cut_v1" in sql:
            return FakeCursor(self.rows["facade"])
        if "pg_control_system()" in sql:
            if self.rows.get("sysid") is None:
                raise PermissionError("sensitive-password-in-synthetic-error")
            if self.after_physical_probe is not None:
                self.after_physical_probe()
            return FakeCursor(self.rows["sysid"])
        raise AssertionError(f"unapproved SQL: {sql}")


class FakeCursor:
    def __init__(self, row: object) -> None:
        self.row = row

    def fetchone(self) -> dict[str, object] | None:
        return self.row if isinstance(self.row, dict) else None

    def fetchall(self) -> list[dict[str, object]]:
        if isinstance(self.row, list):
            return self.row
        return [self.row] if isinstance(self.row, dict) else []


def fixtures() -> tuple[dict[str, object], dict[str, object]]:
    registry = {
        "registry": {
            "project_key": "bt2",
            "target_key": "primary",
            "target_role": "PRIMARY",
            "engine": "postgresql",
            "provider_kind": "external-postgresql",
            "provider_resource_ref": "external-resource-1",
            "database_name": "bt2",
            "lifecycle_state": "RUNNING",
        }
    }
    target = {
        "ssl": {"ssl": True},
        "role": {
            "database_user": "bt2_read",
            "session_user": "bt2_read",
            "rolsuper": False,
            "rolcreatedb": False,
            "rolcreaterole": False,
            "rolreplication": False,
            "rolbypassrls": False,
            "has_read_all_data": False,
            "can_set_read_all_data": False,
            "has_write_all_data": False,
            "can_set_write_all_data": False,
            "has_read_server_files": False,
            "can_set_read_server_files": False,
            "has_write_server_files": False,
            "can_set_write_server_files": False,
            "has_execute_server_program": False,
            "can_set_execute_server_program": False,
            "has_monitor": False,
            "can_set_monitor": False,
            "has_signal_backend": False,
            "can_set_signal_backend": False,
            "has_checkpoint": False,
            "can_set_checkpoint": False,
        },
        "identity": {
            "database_name": "bt2",
            "database_user": "bt2_read",
            "server_version_num": "160000",
        },
        "migration": {"version": "0002", "checksum": "expected-migration-checksum"},
        "facade": {
            "facade_id": "BT2_MATERIAL_CUT_V1",
            "profile_digest": "expected-profile",
            "policy_digest": "expected-policy",
            "material_count": 2,
        },
        "sysid": {"system_identifier": "1234567890123456789"},
    }
    return registry, target


def params(tmp_path: Path) -> tuple[str, str, TargetAdmissionExpectation]:
    ca = tmp_path / "trusted-ca.pem"
    ca.write_text("inert-test-ca-not-used-by-network", encoding="utf-8")
    root = f"sslmode=verify-full sslrootcert={ca}"
    registry_dsn = (
        f"host=registry.example.test dbname=registry user=reader password=reg-secret {root}"
    )
    target_dsn = f"host=target.example.test dbname=bt2 user=bt2_read password=target-secret {root}"
    expectation = TargetAdmissionExpectation(
        project_key="bt2",
        target_key="primary",
        expected_provider_kind="external-postgresql",
        expected_provider_resource_ref="external-resource-1",
        expected_host="target.example.test",
        expected_database="bt2",
        expected_user="bt2_read",
        expected_system_identifier="1234567890123456789",
        expected_migration_version="0002",
        expected_migration_checksum="expected-migration-checksum",
        expected_profile_digest="expected-profile",
        expected_policy_digest="expected-policy",
    )
    return registry_dsn, target_dsn, expectation


def run_case(
    tmp_path: Path,
    *,
    mutate_registry: dict[str, object] | None = None,
    mutate_target: dict[str, object] | None = None,
    target_dsn_replacement: str | None = None,
    mutate_registry_during_target: bool = False,
) -> tuple[dict[str, object], FakeConnection, FakeConnection]:
    registry_dsn, target_dsn, expected = params(tmp_path)
    if target_dsn_replacement is not None:
        target_dsn = target_dsn_replacement
    registry_rows, target_rows = fixtures()
    if mutate_registry:
        registry_rows["registry"].update(mutate_registry)
    if mutate_target:
        target_rows.update(mutate_target)
    registry = FakeConnection(registry_rows)
    target = FakeConnection(
        target_rows,
        after_physical_probe=(
            lambda: (
                registry_rows["registry"].update({"provider_resource_ref": "raced-away"})
                if mutate_registry_during_target
                else None
            )
        ),
    )

    def connect(dsn: str, **kwargs: object) -> FakeConnection:
        assert kwargs["autocommit"] is True
        assert kwargs["connect_timeout"] == 5
        if dsn == registry_dsn:
            return registry
        assert dsn == target_dsn
        return target

    result = admit_postgres_target(registry_dsn, target_dsn, expected, connector=connect)
    return result, registry, target


def test_operator_admission_pass_bounded_and_redacted(tmp_path: Path) -> None:
    result, registry, target = run_case(tmp_path)
    assert result["status"] == "PASS"
    assert result["cutover_authorized"] is False
    assert result["evidence_ceiling"] == "OPERATOR_READONLY_TARGET_ADMISSION"
    assert result["database_grants_state"] == "UNKNOWN"
    assert "FROM sql_connectome.projects" in "".join(registry.queries)
    assert "SET TRANSACTION" in "".join(target.queries)
    assert "FROM pg_catalog.pg_stat_ssl" in "".join(target.queries)
    assert "pg_control_system()" in "".join(target.queries)
    assert sum("FROM sql_connectome.projects" in q for q in registry.queries) == 2
    assert "SET LOCAL search_path = pg_catalog, pg_temp" in "".join(target.queries)
    assert all(
        "FROM pg_catalog." in q
        for q in target.queries
        if "pg_stat_ssl" in q or "pg_roles" in q or "pg_control_system()" in q
    )
    printed = json.dumps(result, sort_keys=True)
    for secret in ("target-secret", "reg-secret", "registry.example.test", "external-resource-1"):
        assert secret not in printed


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ({"database_name": "wrong"}, "REGISTRY_TARGET_MISMATCH"),
        ({"provider_resource_ref": "wrong"}, "REGISTRY_TARGET_MISMATCH"),
        ({"lifecycle_state": "RETIRED"}, "REGISTRY_TARGET_MISMATCH"),
    ],
)
def test_registered_identity_mismatch_fails_before_target_open(
    tmp_path: Path, mutation: dict[str, object], expected_code: str
) -> None:
    result, _, target = run_case(tmp_path, mutate_registry=mutation)
    assert result["status"] == "FAIL"
    assert result["code"] == expected_code
    assert target.queries == []


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ({"ssl": {"ssl": False}}, "TARGET_TLS_NOT_ACTIVE"),
        ({"role": {**fixtures()[1]["role"], "rolsuper": True}}, "TARGET_ROLE_ELEVATED"),
        (
            {
                "identity": {
                    "database_name": "other",
                    "database_user": "bt2_read",
                    "server_version_num": "160000",
                }
            },
            "TARGET_IDENTITY_MISMATCH",
        ),
        ({"migration": {"version": "0002", "checksum": "wrong"}}, "TARGET_MIGRATION_MISMATCH"),
        (
            {
                "facade": {
                    "facade_id": "WRONG",
                    "profile_digest": "expected-profile",
                    "policy_digest": "expected-policy",
                    "material_count": 2,
                }
            },
            "TARGET_FACADE_MISMATCH",
        ),
        ({"sysid": {"system_identifier": "000"}}, "TARGET_CLUSTER_MISMATCH"),
        (
            {"role": {**fixtures()[1]["role"], "can_set_write_all_data": True}},
            "TARGET_ROLE_ELEVATED",
        ),
        (
            {"role": {**fixtures()[1]["role"], "session_user": "postgres"}},
            "TARGET_IDENTITY_MISMATCH",
        ),
        (
            {"facade": [fixtures()[1]["facade"], fixtures()[1]["facade"]]},
            "TARGET_FACADE_MISMATCH",
        ),
    ],
)
def test_target_falsifiers_fail(
    tmp_path: Path, mutation: dict[str, object], expected_code: str
) -> None:
    result, _, _ = run_case(tmp_path, mutate_target=mutation)
    assert result["status"] == "FAIL"
    assert result["code"] == expected_code


def test_missing_cluster_identification_is_unknown_not_pass(tmp_path: Path) -> None:
    result, _, _ = run_case(tmp_path, mutate_target={"sysid": None})
    assert result["status"] == "UNKNOWN"
    assert result["code"] == "TARGET_CLUSTER_PROBE_UNAVAILABLE"
    assert "sensitive-password" not in json.dumps(result)


def test_registry_rebinding_mid_probe_is_unknown(tmp_path: Path) -> None:
    result, registry, target = run_case(tmp_path, mutate_registry_during_target=True)
    assert result["status"] == "UNKNOWN"
    assert result["code"] == "REGISTRY_BINDING_CHANGED"
    assert sum("FROM sql_connectome.projects" in q for q in registry.queries) == 2
    assert "pg_control_system()" in "".join(target.queries)


def test_non_verify_full_target_dsn_denied_before_any_connection(tmp_path: Path) -> None:
    bad = "host=target.example.test dbname=bt2 user=bt2_read sslmode=require"
    result, registry, target = run_case(tmp_path, target_dsn_replacement=bad)
    assert result["status"] == "FAIL"
    assert result["code"] == "TARGET_TLS_CONFIG_UNSAFE"
    assert not registry.queries and not target.queries
