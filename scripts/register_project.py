from __future__ import annotations

import argparse
import json
import os

from sql_connectome.projects import register_project


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register a SQL Connectome project through the operator-only write path."
    )
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--metadata-json", default="{}")
    args = parser.parse_args()

    metadata = json.loads(args.metadata_json)
    if not isinstance(metadata, dict):
        raise SystemExit("--metadata-json must decode to a JSON object")

    result = register_project(
        os.environ["SQL_CONNECTOME_DATABASE_URL"],
        project_key=args.project_key,
        display_name=args.display_name,
        metadata=metadata,
    )
    print(json.dumps(result, sort_keys=True, indent=2, default=str))


if __name__ == "__main__":
    main()
