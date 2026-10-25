"""Fail-closed accidental-use guard for a disposable GitHub PostgreSQL service.

This is a safety interlock, not an attestation against intentionally spoofed CI
environment variables. The live fixture must never target a persistent DB.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict


def require_disposable_pg16_ci(environ: Mapping[str, str]) -> Path:
    """Validate exact CI inputs before opening any connection or altering state."""
    failure = RuntimeError("ADMISSION_FIXTURE_REQUIRES_DISPOSABLE_PG16_CI")
    if (
        environ.get("BT2_SQL_V4_EPHEMERAL_QUALIFICATION") != "1"
        or environ.get("GITHUB_ACTIONS") != "true"
        or environ.get("GITHUB_REPOSITORY") != "thebrazenbeard/sql-connectome"
        or not re.fullmatch(r"[0-9a-f]{64}", environ.get("POSTGRES_CONTAINER_ID", ""))
        # Earlier workflow steps also issue SQL: bind their connection target
        # to loopback at the job level. Reject alternate libpq overrides.
        or environ.get("PGHOSTADDR") != "127.0.0.1"
        or any(key.upper().startswith("PG") and key != "PGHOSTADDR" for key in environ)
    ):
        raise failure

    try:
        connection = conninfo_to_dict(environ.get("DATABASE_URL", ""))
    except (psycopg.Error, ValueError, TypeError) as exc:
        raise failure from exc
    if (
        set(connection) - {"host", "port", "dbname", "user", "password"}
        or connection.get("host") != "localhost"
        or connection.get("port") != "5432"
        or connection.get("dbname") != "bt2_sql_ci"
        or connection.get("user") != "postgres"
        or connection.get("password") != "postgres"
    ):
        raise failure

    runner_temp = environ.get("RUNNER_TEMP")
    ca_path = environ.get("BT2_ADMISSION_CA_PATH")
    if not runner_temp or not ca_path:
        raise failure
    expected = Path(runner_temp).resolve() / "pg16-admission.crt"
    if Path(ca_path).resolve() != expected or not expected.is_file():
        raise failure
    return expected
