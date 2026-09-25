from __future__ import annotations

import argparse
import json
import os

from sql_connectome.projects import register_database_target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register a non-secret database target for a SQL Connectome project."
    )
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--target-key", required=True)
    parser.add_argument("--provider-kind", required=True)
    parser.add_argument("--database-name", required=True)
    parser.add_argument(
        "--target-role",
        choices=("PRIMARY", "REPLICA", "ANALYTICS", "ARCHIVE"),
        default="PRIMARY",
    )
    parser.add_argument("--engine", default="postgresql")
    parser.add_argument("--provider-resource-ref")
    parser.add_argument("--region")
    parser.add_argument(
        "--lifecycle-state",
        choices=(
            "REGISTERED",
            "PROVISIONING",
            "RUNNING",
            "DEGRADED",
            "STOPPED",
            "RETIRED",
            "UNKNOWN",
        ),
        default="REGISTERED",
    )
    parser.add_argument("--capabilities-json", default="{}")
    parser.add_argument("--metadata-json", default="{}")
    args = parser.parse_args()

    capabilities = json.loads(args.capabilities_json)
    metadata = json.loads(args.metadata_json)
    if not isinstance(capabilities, dict):
        raise SystemExit("--capabilities-json must decode to a JSON object")
    if not isinstance(metadata, dict):
        raise SystemExit("--metadata-json must decode to a JSON object")

    result = register_database_target(
        os.environ["SQL_CONNECTOME_DATABASE_URL"],
        project_key=args.project_key,
        target_key=args.target_key,
        provider_kind=args.provider_kind,
        database_name=args.database_name,
        target_role=args.target_role,
        engine=args.engine,
        provider_resource_ref=args.provider_resource_ref,
        region=args.region,
        lifecycle_state=args.lifecycle_state,
        capabilities=capabilities,
        metadata=metadata,
    )
    print(json.dumps(result, sort_keys=True, indent=2, default=str))


if __name__ == "__main__":
    main()
