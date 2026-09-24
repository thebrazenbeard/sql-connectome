from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from .db import _runtime_identity
from .receipts import canonical_digest, canonical_json, make_receipt

BACKUP_SCHEMA = "SQL_CONNECTOME_BACKUP_MANIFEST_V1"
RESTORE_SCHEMA = "SQL_CONNECTOME_RESTORE_RECEIPT_V1"


class RecoveryError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitized_conninfo(dsn: str) -> tuple[str, str | None]:
    params = conninfo_to_dict(dsn)
    password = params.pop("password", None)
    return make_conninfo(**params), password


def _tool_version(binary: str) -> str:
    result = subprocess.run(
        [binary, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RecoveryError(f"POSTGRES_TOOL_VERSION_FAILED:{binary}")
    return result.stdout.strip()


def _major_from_version(version: str) -> int:
    match = re.search(r"(\d+)(?:\.\d+)?", version)
    if not match:
        raise RecoveryError(f"POSTGRES_TOOL_VERSION_UNPARSEABLE:{version}")
    return int(match.group(1))


def _run_postgres_tool(binary: str, args: list[str], dsn: str) -> subprocess.CompletedProcess[str]:
    sanitized, password = _sanitized_conninfo(dsn)
    env = os.environ.copy()
    if password is not None:
        env["PGPASSWORD"] = password

    result = subprocess.run(
        [binary, "--dbname", sanitized, *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        detail = message[-1] if message else "unknown error"
        raise RecoveryError(f"POSTGRES_TOOL_FAILED:{Path(binary).name}:{detail}")
    return result


def _catalog_state(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, Any]:
    schemas = conn.execute(
        """
        SELECT nspname
        FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema')
          AND nspname NOT LIKE 'pg_toast%'
          AND nspname NOT LIKE 'pg_temp_%'
        ORDER BY nspname
        """
    ).fetchall()

    relations = conn.execute(
        """
        SELECT n.nspname AS schema_name, c.relname AS relation_name, c.relkind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND n.nspname NOT LIKE 'pg_temp_%'
          AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
        ORDER BY n.nspname, c.relname, c.relkind
        """
    ).fetchall()

    functions = conn.execute(
        """
        SELECT n.nspname AS schema_name,
               p.proname AS function_name,
               pg_get_function_identity_arguments(p.oid) AS identity_arguments
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND n.nspname NOT LIKE 'pg_temp_%'
        ORDER BY n.nspname, p.proname, identity_arguments
        """
    ).fetchall()

    extensions = conn.execute(
        """
        SELECT e.extname, e.extversion, n.nspname AS schema_name
        FROM pg_extension e
        JOIN pg_namespace n ON n.oid = e.extnamespace
        ORDER BY e.extname
        """
    ).fetchall()

    state = {
        "schemas": [row["nspname"] for row in schemas],
        "relations": [
            [row["schema_name"], row["relation_name"], row["relkind"]]
            for row in relations
        ],
        "functions": [
            [row["schema_name"], row["function_name"], row["identity_arguments"]]
            for row in functions
        ],
        "extensions": [
            [row["extname"], row["extversion"], row["schema_name"]]
            for row in extensions
        ],
    }
    return {
        **state,
        "catalog_digest": canonical_digest(state),
        "counts": {
            "schemas": len(state["schemas"]),
            "relations": len(state["relations"]),
            "functions": len(state["functions"]),
            "extensions": len(state["extensions"]),
        },
    }


def _migration_state(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, Any]:
    ledger = conn.execute(
        "SELECT to_regclass('sql_connectome.schema_migrations')::text AS ledger"
    ).fetchone()
    rows: list[dict[str, Any]] = []
    if ledger and ledger["ledger"]:
        rows = conn.execute(
            """
            SELECT version, checksum, source_path
            FROM sql_connectome.schema_migrations
            ORDER BY version
            """
        ).fetchall()

    members = [[row["version"], row["checksum"], row["source_path"]] for row in rows]
    return {
        "applied_count": len(members),
        "members": members,
        "migration_digest": canonical_digest(members),
    }


def _blank_target_state(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, int]:
    schemas = conn.execute(
        """
        SELECT count(*) AS count
        FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'public')
          AND nspname NOT LIKE 'pg_toast%'
          AND nspname NOT LIKE 'pg_temp_%'
        """
    ).fetchone()["count"]

    relations = conn.execute(
        """
        SELECT count(*) AS count
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND n.nspname NOT LIKE 'pg_temp_%'
          AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
        """
    ).fetchone()["count"]

    functions = conn.execute(
        """
        SELECT count(*) AS count
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND n.nspname NOT LIKE 'pg_temp_%'
        """
    ).fetchone()["count"]

    extensions = conn.execute(
        "SELECT count(*) AS count FROM pg_extension WHERE extname <> 'plpgsql'"
    ).fetchone()["count"]

    types = conn.execute(
        """
        SELECT count(*) AS count
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND n.nspname NOT LIKE 'pg_temp_%'
          AND t.typrelid = 0
          AND t.typelem = 0
          AND t.typtype IN ('c', 'd', 'e', 'r', 'm')
        """
    ).fetchone()["count"]

    return {
        "schemas": int(schemas),
        "relations": int(relations),
        "functions": int(functions),
        "extensions": int(extensions),
        "types": int(types),
    }


def _manifest_path_for(archive_path: Path) -> Path:
    return archive_path.with_name(f"{archive_path.name}.manifest.json")


def _validate_manifest_dict(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != BACKUP_SCHEMA:
        raise RecoveryError("BACKUP_MANIFEST_SCHEMA_UNSUPPORTED")
    supplied = manifest.get("manifest_digest")
    if not isinstance(supplied, str):
        raise RecoveryError("BACKUP_MANIFEST_DIGEST_MISSING")
    body = {key: value for key, value in manifest.items() if key != "manifest_digest"}
    if canonical_digest(body) != supplied:
        raise RecoveryError("BACKUP_MANIFEST_DIGEST_MISMATCH")


def create_backup(
    database_url: str,
    archive_path: Path,
    *,
    pg_dump_bin: str = "pg_dump",
    overwrite: bool = False,
    lock_wait_timeout: str = "10s",
) -> dict[str, Any]:
    archive = archive_path.resolve()
    manifest_path = _manifest_path_for(archive)

    if not overwrite and (archive.exists() or manifest_path.exists()):
        raise RecoveryError("BACKUP_TARGET_EXISTS")

    archive.parent.mkdir(parents=True, exist_ok=True)
    temp_archive = archive.with_name(f".{archive.name}.tmp-{uuid4().hex}")
    temp_manifest = manifest_path.with_name(f".{manifest_path.name}.tmp-{uuid4().hex}")

    pg_dump_version = _tool_version(pg_dump_bin)
    pg_dump_major = _major_from_version(pg_dump_version)

    try:
        with psycopg.connect(
            database_url,
            autocommit=False,
            row_factory=dict_row,
            application_name="sql-connectome-backup",
        ) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                snapshot = conn.execute("SELECT pg_export_snapshot() AS snapshot").fetchone()
                assert snapshot is not None
                snapshot_id = str(snapshot["snapshot"])
                runtime = _runtime_identity(conn)
                source_server_major = int(str(runtime["server_version_num"])) // 10000
                if pg_dump_major < source_server_major:
                    raise RecoveryError("PG_DUMP_MAJOR_OLDER_THAN_SERVER")

                catalog = _catalog_state(conn)
                migrations = _migration_state(conn)

                dump = _run_postgres_tool(
                    pg_dump_bin,
                    [
                        "--format=custom",
                        "--no-owner",
                        "--no-privileges",
                        f"--snapshot={snapshot_id}",
                        f"--lock-wait-timeout={lock_wait_timeout}",
                        f"--file={temp_archive}",
                    ],
                    database_url,
                )

        if not temp_archive.exists() or temp_archive.stat().st_size == 0:
            raise RecoveryError("BACKUP_ARCHIVE_EMPTY")

        backup_sha256 = _sha256_file(temp_archive)
        body: dict[str, Any] = {
            "schema": BACKUP_SCHEMA,
            "created_at": datetime.now(UTC).isoformat(),
            "format": "postgres-custom",
            "backup_file": archive.name,
            "backup_sha256": backup_sha256,
            "backup_size_bytes": temp_archive.stat().st_size,
            "pg_dump_version": pg_dump_version,
            "pg_dump_major": pg_dump_major,
            "snapshot_id": snapshot_id,
            "source_runtime": runtime,
            "source_catalog_digest": catalog["catalog_digest"],
            "source_catalog_counts": catalog["counts"],
            "source_migration_digest": migrations["migration_digest"],
            "source_migration_count": migrations["applied_count"],
            "pg_dump_stderr": dump.stderr.strip()[:4096],
            "ownership_preserved": False,
            "privileges_preserved": False,
        }
        manifest = {**body, "manifest_digest": canonical_digest(body)}
        temp_manifest.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")

        os.replace(temp_archive, archive)
        os.replace(temp_manifest, manifest_path)
        return manifest
    except Exception:
        temp_archive.unlink(missing_ok=True)
        temp_manifest.unlink(missing_ok=True)
        raise


def load_and_verify_backup(
    archive_path: Path,
    *,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    archive = archive_path.resolve()
    manifest_file = (manifest_path or _manifest_path_for(archive)).resolve()

    if not archive.is_file():
        raise RecoveryError("BACKUP_ARCHIVE_MISSING")
    if not manifest_file.is_file():
        raise RecoveryError("BACKUP_MANIFEST_MISSING")

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RecoveryError("BACKUP_MANIFEST_INVALID_JSON") from exc

    if not isinstance(manifest, dict):
        raise RecoveryError("BACKUP_MANIFEST_INVALID")
    _validate_manifest_dict(manifest)

    actual_size = archive.stat().st_size
    if actual_size != manifest.get("backup_size_bytes"):
        raise RecoveryError("BACKUP_SIZE_MISMATCH")

    actual_digest = _sha256_file(archive)
    if actual_digest != manifest.get("backup_sha256"):
        raise RecoveryError("BACKUP_ARCHIVE_DIGEST_MISMATCH")

    return manifest


def restore_backup(
    target_database_url: str,
    archive_path: Path,
    *,
    manifest_path: Path | None = None,
    pg_restore_bin: str = "pg_restore",
    trusted_source: bool = False,
) -> dict[str, Any]:
    if not trusted_source:
        raise RecoveryError("RESTORE_REQUIRES_TRUSTED_SOURCE_ACKNOWLEDGEMENT")

    archive = archive_path.resolve()
    manifest = load_and_verify_backup(archive, manifest_path=manifest_path)
    pg_restore_version = _tool_version(pg_restore_bin)
    pg_restore_major = _major_from_version(pg_restore_version)

    source_major = int(manifest["source_runtime"]["server_version_num"]) // 10000
    if pg_restore_major < int(manifest["pg_dump_major"]):
        raise RecoveryError("PG_RESTORE_MAJOR_OLDER_THAN_BACKUP_TOOL")

    with psycopg.connect(
        target_database_url,
        autocommit=True,
        row_factory=dict_row,
        application_name="sql-connectome-restore-preflight",
    ) as conn:
        blank = _blank_target_state(conn)
        if any(blank.values()):
            raise RecoveryError(f"RECOVERY_TARGET_NOT_BLANK:{canonical_json(blank)}")
        target_runtime_before = _runtime_identity(conn)
        target_major = int(str(target_runtime_before["server_version_num"])) // 10000
        if target_major < source_major:
            raise RecoveryError("RECOVERY_TARGET_SERVER_OLDER_THAN_SOURCE")

    restore = _run_postgres_tool(
        pg_restore_bin,
        [
            "--exit-on-error",
            "--single-transaction",
            "--no-owner",
            "--no-privileges",
            str(archive),
        ],
        target_database_url,
    )

    with psycopg.connect(
        target_database_url,
        autocommit=True,
        row_factory=dict_row,
        application_name="sql-connectome-restore-verify",
    ) as conn:
        target_runtime = _runtime_identity(conn)
        target_catalog = _catalog_state(conn)
        target_migrations = _migration_state(conn)

    checks = {
        "catalog_digest_matches": (
            target_catalog["catalog_digest"] == manifest["source_catalog_digest"]
        ),
        "migration_digest_matches": (
            target_migrations["migration_digest"] == manifest["source_migration_digest"]
        ),
        "migration_count_matches": (
            target_migrations["applied_count"] == manifest["source_migration_count"]
        ),
    }
    if not all(checks.values()):
        raise RecoveryError(f"RESTORE_QUALIFICATION_FAILED:{canonical_json(checks)}")

    subject = {
        "backup_sha256": manifest["backup_sha256"],
        "manifest_digest": manifest["manifest_digest"],
        "source_runtime_identity_digest": manifest["source_runtime"]["identity_digest"],
        "target_runtime_identity_digest": target_runtime["identity_digest"],
        "checks": checks,
    }
    return {
        "schema": RESTORE_SCHEMA,
        "status": "PASS",
        "archive": {
            "sha256": manifest["backup_sha256"],
            "size_bytes": manifest["backup_size_bytes"],
            "manifest_digest": manifest["manifest_digest"],
        },
        "source_runtime": manifest["source_runtime"],
        "target_runtime": target_runtime,
        "checks": checks,
        "pg_restore_version": pg_restore_version,
        "pg_restore_stderr": restore.stderr.strip()[:4096],
        "receipt": make_receipt("DATABASE_RESTORE_QUALIFICATION", subject),
    }
