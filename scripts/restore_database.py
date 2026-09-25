from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sql_connectome.recovery import restore_backup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore a trusted SQL Connectome backup into a blank PostgreSQL database."
    )
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--pg-restore-bin",
        default=os.getenv("SQL_CONNECTOME_PG_RESTORE_BIN", "pg_restore"),
    )
    parser.add_argument(
        "--trusted-source",
        action="store_true",
        help="Acknowledge that PostgreSQL restores can execute code contained in the dump.",
    )
    args = parser.parse_args()

    target_url = os.environ["SQL_CONNECTOME_RESTORE_DATABASE_URL"]
    receipt = restore_backup(
        target_url,
        args.archive,
        manifest_path=args.manifest,
        pg_restore_bin=args.pg_restore_bin,
        trusted_source=args.trusted_source,
    )
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
