"""Inert regressions for observable backup destination path redirection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

import sql_connectome.recovery as recovery
from sql_connectome.recovery import RecoveryError


def _must_not_start_backup(_binary: str) -> str:
    pytest.fail("backup tools were reached before rejecting the unsafe output path")


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")


@pytest.mark.parametrize("case", ["leaf", "dangling_leaf", "ancestor", "manifest_leaf"])
@pytest.mark.parametrize("overwrite", [False, True])
def test_backup_rejects_symlink_components_before_pg_dump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, overwrite: bool,
) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    archive = tmp_path / "backup.dump"

    if case == "leaf":
        target = real_directory / "existing.dump"
        target.write_bytes(b"sentinel")
        _symlink_or_skip(archive, target)
    elif case == "dangling_leaf":
        target = real_directory / "missing.dump"
        _symlink_or_skip(archive, target)
    elif case == "ancestor":
        alias = tmp_path / "alias"
        _symlink_or_skip(alias, real_directory, directory=True)
        archive = alias / "backup.dump"
    else:
        manifest = archive.with_name(f"{archive.name}.manifest.json")
        target = real_directory / "missing-manifest.json"
        _symlink_or_skip(manifest, target)

    monkeypatch.setattr(recovery, "_tool_version", _must_not_start_backup)
    with pytest.raises(RecoveryError, match="BACKUP_PATH_LINK_FORBIDDEN"):
        recovery.create_backup("postgresql://unused", archive, overwrite=overwrite)

    if case in ("leaf", "dangling_leaf"):
        assert archive.is_symlink()
        if case == "leaf":
            assert target.read_bytes() == b"sentinel"
        else:
            assert not target.exists()
    elif case == "manifest_leaf":
        assert manifest.is_symlink()
        assert not target.exists()


def test_backup_allows_new_regular_nested_destination_to_reach_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "nested" / "backup.dump"

    def reached_preflight(_binary: str) -> str:
        raise RuntimeError("REACHED_SAFE_PREFLIGHT")

    monkeypatch.setattr(recovery, "_tool_version", reached_preflight)
    with pytest.raises(RuntimeError, match="REACHED_SAFE_PREFLIGHT"):
        recovery.create_backup("postgresql://unused", archive)
    assert archive.parent.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows directory junctions")
def test_backup_rejects_windows_directory_junction_before_pg_dump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    junction = tmp_path / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real_directory)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0 or not junction.is_junction():
        pytest.skip("Windows junction creation unavailable")

    monkeypatch.setattr(recovery, "_tool_version", _must_not_start_backup)
    with pytest.raises(RecoveryError, match="BACKUP_PATH_LINK_FORBIDDEN"):
        recovery.create_backup("postgresql://unused", junction / "backup.dump")
