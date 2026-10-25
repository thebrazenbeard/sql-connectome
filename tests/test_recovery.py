import json
import os
from pathlib import Path
from subprocess import CompletedProcess

import pytest

import sql_connectome.recovery as recovery
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


def _restore_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    archive = tmp_path / "backup.dump"
    archive.write_bytes(b"known-good-archive-bytes")
    _write_manifest(
        archive,
        pg_dump_major=17,
        source_runtime={"server_version_num": "170000", "identity_digest": "source"},
        source_catalog_digest="catalog",
        source_migration_digest="migrations",
        source_migration_count=0,
    )

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr(recovery.psycopg, "connect", lambda *_a, **_kw: FakeConnection())
    monkeypatch.setattr(recovery, "_tool_version", lambda _bin: "pg_restore (PostgreSQL) 17.0")
    monkeypatch.setattr(recovery, "_blank_target_state", lambda _conn: {"relations": 0})
    monkeypatch.setattr(
        recovery, "_runtime_identity",
        lambda _conn: {"server_version_num": "170000", "identity_digest": "target"},
    )
    monkeypatch.setattr(recovery, "_catalog_state", lambda _conn: {"catalog_digest": "catalog"})
    monkeypatch.setattr(
        recovery, "_migration_state",
        lambda _conn: {"migration_digest": "migrations", "applied_count": 0},
    )
    return archive


def test_restore_does_not_consume_archive_swapped_after_initial_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = _restore_fixture(tmp_path, monkeypatch)
    original_load = recovery.load_and_verify_backup

    def verified_then_swapped(*args, **kwargs):
        result = original_load(*args, **kwargs)
        archive.write_bytes(b"x" * len(b"known-good-archive-bytes"))
        return result

    monkeypatch.setattr(recovery, "load_and_verify_backup", verified_then_swapped)

    def unexpected_restore(*_args, **_kwargs):
        pytest.fail("pg_restore called on archive changed after verification")

    monkeypatch.setattr(recovery, "_run_postgres_tool", unexpected_restore)
    with pytest.raises(RecoveryError, match="RESTORE_STAGED_ARCHIVE_DIGEST_MISMATCH"):
        restore_backup("postgresql://unused", archive, trusted_source=True)


def test_restore_consumes_private_verified_copy_not_caller_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = _restore_fixture(tmp_path, monkeypatch)
    staged: list[Path] = []

    def observed_restore(_binary, args, _dsn):
        input_path = Path(args[-1])
        staged.append(input_path)
        assert input_path != archive
        assert input_path.read_bytes() == archive.read_bytes()
        return CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(recovery, "_run_postgres_tool", observed_restore)
    result = restore_backup("postgresql://unused", archive, trusted_source=True)
    assert result["status"] == "PASS"
    assert len(staged) == 1
    assert not staged[0].exists()  # Temporary staging is deleted after pg_restore exits.


def test_staging_never_reads_unbounded_growing_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "regular.dump"
    archive.write_bytes(b"regular-file")
    private = tmp_path / "private"
    private.mkdir()
    calls: list[int] = []
    original_fdopen = os.fdopen

    class GrowingSource:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            self.file.close()

        def fileno(self):
            return self.file.fileno()

        def read(self, length):
            calls.append(length)
            if len(calls) > 2:
                pytest.fail("unbounded read of concurrently growing archive")
            return b"x" * length

    monkeypatch.setattr(
        recovery.os, "fdopen",
        lambda descriptor, mode: GrowingSource(original_fdopen(descriptor, mode)),
    )

    with pytest.raises(RecoveryError, match="RESTORE_STAGED_ARCHIVE_SIZE_MISMATCH"):
        recovery._stage_verified_restore_archive(
            archive, {"backup_size_bytes": 16}, private,
        )
    assert calls == [16, 1]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX named pipes")
def test_staging_rejects_swapped_fifo_without_waiting_for_writer(tmp_path: Path) -> None:
    fifo = tmp_path / "swapped.dump"
    os.mkfifo(fifo)
    private = tmp_path / "private"
    private.mkdir()
    with pytest.raises(RecoveryError, match="RESTORE_STAGED_ARCHIVE_NOT_REGULAR"):
        recovery._stage_verified_restore_archive(
            fifo, {"backup_size_bytes": 16}, private,
        )
