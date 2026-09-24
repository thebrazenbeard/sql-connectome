from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "database" / "migrations"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    dsn = os.environ["SQL_CONNECTOME_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True, application_name="sql-connectome-migrator") as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS sql_connectome")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sql_connectome.schema_migrations (
                version text PRIMARY KEY,
                checksum text NOT NULL,
                source_path text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
            )
            """
        )

        for path in sorted(MIGRATIONS.glob("*.sql")):
            version = path.stem.split("_", 1)[0]
            data = path.read_bytes()
            checksum = digest(data)
            existing = conn.execute(
                "SELECT checksum FROM sql_connectome.schema_migrations WHERE version = %s",
                (version,),
            ).fetchone()
            if existing:
                if existing[0] != checksum:
                    raise RuntimeError(f"MIGRATION_CHECKSUM_MISMATCH:{version}")
                continue

            with conn.transaction():
                conn.execute(data.decode("utf-8"))
                conn.execute(
                    """
                    INSERT INTO sql_connectome.schema_migrations(version, checksum, source_path)
                    VALUES (%s, %s, %s)
                    """,
                    (version, checksum, str(path.relative_to(ROOT))),
                )
            print(f"applied {version} {checksum}")


if __name__ == "__main__":
    main()
