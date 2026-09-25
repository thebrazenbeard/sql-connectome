from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sql_connectome.recovery import create_backup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a checksum-bound SQL Connectome PostgreSQL backup."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--pg-dump-bin",
        default=os.getenv("SQL_CONNECTOME_PG_DUMP_BIN", "pg_dump"),
    )
    parser.add_argument("--lock-wait-timeout", default="10s")
    args = parser.parse_args()

    database_url = os.environ["SQL_CONNECTOME_DATABASE_URL"]
    manifest = create_backup(
        database_url,
        args.output,
        pg_dump_bin=args.pg_dump_bin,
        overwrite=args.overwrite,
        lock_wait_timeout=args.lock_wait_timeout,
    )
    print(json.dumps(manifest, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
