"""Portable negative checks: never connect or mutate a database."""

from __future__ import annotations

import pytest
from ci_admission_guard import require_disposable_pg16_ci


def _safe_ci_env(tmp_path):
    ca_path = tmp_path / "pg16-admission.crt"
    ca_path.write_text("test-only CA marker\n", encoding="ascii")
    return {
        "BT2_SQL_V4_EPHEMERAL_QUALIFICATION": "1",
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "thebrazenbeard/sql-connectome",
        "POSTGRES_CONTAINER_ID": "a" * 64,
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/bt2_sql_ci",
        "RUNNER_TEMP": str(tmp_path),
        "BT2_ADMISSION_CA_PATH": str(ca_path),
    }


def test_disposable_ci_gate_accepts_only_expected_fixture_shape(tmp_path):
    env = _safe_ci_env(tmp_path)
    assert require_disposable_pg16_ci(env) == tmp_path / "pg16-admission.crt"


@pytest.mark.parametrize(
    ("key", "bad_value"),
    [
        ("BT2_SQL_V4_EPHEMERAL_QUALIFICATION", "0"),
        ("GITHUB_ACTIONS", "false"),
        ("GITHUB_REPOSITORY", "thebrazenbeard/another-repo"),
        ("POSTGRES_CONTAINER_ID", ""),
        ("POSTGRES_CONTAINER_ID", "a" * 12),
        ("DATABASE_URL", "postgresql://postgres:postgres@db.example:5432/bt2_sql_ci"),
        ("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/production"),
        ("DATABASE_URL", "postgresql://root:postgres@localhost:5432/bt2_sql_ci"),
        ("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/bt2_sql_ci"),
        ("DATABASE_URL", "postgresql://postgres:bad@localhost:5432/bt2_sql_ci"),
        (
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/bt2_sql_ci?hostaddr=127.0.0.2",
        ),
        (
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/bt2_sql_ci?service=prod",
        ),
        ("DATABASE_URL", "not a database url"),
        ("BT2_ADMISSION_CA_PATH", "/tmp/some-other-root.crt"),
        ("RUNNER_TEMP", ""),
    ],
)
def test_disposable_ci_gate_rejects_unsafe_environment(tmp_path, key, bad_value):
    env = _safe_ci_env(tmp_path)
    env[key] = bad_value
    with pytest.raises(RuntimeError, match="ADMISSION_FIXTURE_REQUIRES_DISPOSABLE_PG16_CI"):
        require_disposable_pg16_ci(env)


@pytest.mark.parametrize(
    "missing",
    [
        "GITHUB_ACTIONS",
        "GITHUB_REPOSITORY",
        "POSTGRES_CONTAINER_ID",
        "DATABASE_URL",
        "BT2_ADMISSION_CA_PATH",
    ],
)
def test_disposable_ci_gate_rejects_missing_fields(tmp_path, missing):
    env = _safe_ci_env(tmp_path)
    del env[missing]
    with pytest.raises(RuntimeError, match="ADMISSION_FIXTURE_REQUIRES_DISPOSABLE_PG16_CI"):
        require_disposable_pg16_ci(env)


def test_disposable_ci_gate_rejects_missing_ca_file(tmp_path):
    env = _safe_ci_env(tmp_path)
    (tmp_path / "pg16-admission.crt").unlink()
    with pytest.raises(RuntimeError, match="ADMISSION_FIXTURE_REQUIRES_DISPOSABLE_PG16_CI"):
        require_disposable_pg16_ci(env)
