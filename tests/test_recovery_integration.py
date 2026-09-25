import os
from pathlib import Path

import psycopg
import pytest

from sql_connectome.recovery import RecoveryError, create_backup, restore_backup

SOURCE_DSN = os.getenv("SQL_CONNECTOME_DATABASE_URL")
TARGET_DSN = os.getenv("SQL_CONNECTOME_RECOVERY_TARGET_URL")
PG_DUMP_BIN = os.getenv("SQL_CONNECTOME_PG_DUMP_BIN")
PG_RESTORE_BIN = os.getenv("SQL_CONNECTOME_PG_RESTORE_BIN")

pytestmark = pytest.mark.skipif(
    not all((SOURCE_DSN, TARGET_DSN, PG_DUMP_BIN, PG_RESTORE_BIN)),
    reason="recovery qualification environment not configured",
)


def test_backup_restore_roundtrip_and_blank_target_guard(tmp_path: Path) -> None:
    assert SOURCE_DSN and TARGET_DSN and PG_DUMP_BIN and PG_RESTORE_BIN

    with psycopg.connect(SOURCE_DSN, autocommit=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sql_connectome.recovery_qualification_fixture (
                id integer PRIMARY KEY,
                payload text NOT NULL
            )
            """
        )
        conn.execute("TRUNCATE sql_connectome.recovery_qualification_fixture")
        conn.execute(
            """
            INSERT INTO sql_connectome.recovery_qualification_fixture(id, payload)
            VALUES (1, 'alpha'), (2, 'beta')
            """
        )

    archive = tmp_path / "qualified-backup.dump"
    manifest = create_backup(
        SOURCE_DSN,
        archive,
        pg_dump_bin=PG_DUMP_BIN,
    )

    assert manifest["schema"] == "SQL_CONNECTOME_BACKUP_MANIFEST_V1"
    assert manifest["backup_sha256"]
    assert manifest["source_migration_count"] >= 1

    receipt = restore_backup(
        TARGET_DSN,
        archive,
        pg_restore_bin=PG_RESTORE_BIN,
        trusted_source=True,
    )

    assert receipt["status"] == "PASS"
    assert all(receipt["checks"].values())

    with psycopg.connect(TARGET_DSN) as conn:
        rows = conn.execute(
            """
            SELECT id, payload
            FROM sql_connectome.recovery_qualification_fixture
            ORDER BY id
            """
        ).fetchall()
    assert rows == [(1, "alpha"), (2, "beta")]

    with pytest.raises(RecoveryError, match="RECOVERY_TARGET_NOT_BLANK"):
        restore_backup(
            TARGET_DSN,
            archive,
            pg_restore_bin=PG_RESTORE_BIN,
            trusted_source=True,
        )
