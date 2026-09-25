import json
from pathlib import Path

import pytest

from sql_connectome.receipts import canonical_digest
from sql_connectome.recovery import (
    BACKUP_SCHEMA,
    RecoveryError,
    _major_from_version,
    _sanitized_conninfo,
    load_and_verify_backup,
    restore_backup,
)


def _write_manifest(archive: Path, **overrides: object) -> Path:
    body: dict[str, object] = {
        "schema": BACKUP_SCHEMA,
        "backup_size_bytes": archive.stat().st_size,
        "backup_sha256": __import__("hashlib").sha256(archive.read_bytes()).hexdigest(),
    }
    body.update(overrides)
    manifest = {**body, "manifest_digest": canonical_digest(body)}
    path = archive.with_name(f"{archive.name}.manifest.json")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_sanitized_conninfo_removes_password() -> None:
    conninfo, password = _sanitized_conninfo(
        "postgresql://alice:secret@db.example.test:5432/example?sslmode=require"
    )
    assert "secret" not in conninfo
    assert "password" not in conninfo
    assert password == "secret"
    assert "sslmode=require" in conninfo


@pytest.mark.parametrize(
    ("version", "major"),
    [
        ("pg_dump (PostgreSQL) 17.11", 17),
        ("pg_restore (PostgreSQL) 16.4", 16),
    ],
)
def test_postgres_tool_major(version: str, major: int) -> None:
    assert _major_from_version(version) == major


def test_backup_verification_detects_archive_tampering(tmp_path: Path) -> None:
    archive = tmp_path / "backup.dump"
    archive.write_bytes(b"original")
    _write_manifest(archive)

    load_and_verify_backup(archive)
    archive.write_bytes(b"tampered")

    with pytest.raises(RecoveryError, match="BACKUP_(SIZE|ARCHIVE_DIGEST)_MISMATCH"):
        load_and_verify_backup(archive)


def test_backup_verification_detects_manifest_tampering(tmp_path: Path) -> None:
    archive = tmp_path / "backup.dump"
    archive.write_bytes(b"original")
    manifest_path = _write_manifest(archive)
    manifest = json.loads(manifest_path.read_text())
    manifest["backup_size_bytes"] = 999
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(RecoveryError, match="BACKUP_MANIFEST_DIGEST_MISMATCH"):
        load_and_verify_backup(archive)


def test_restore_requires_trusted_source_before_touching_files(tmp_path: Path) -> None:
    with pytest.raises(
        RecoveryError,
        match="RESTORE_REQUIRES_TRUSTED_SOURCE_ACKNOWLEDGEMENT",
    ):
        restore_backup(
            "postgresql://unused",
            tmp_path / "missing.dump",
            trusted_source=False,
        )
