"""Operator-only, read-only admission for a separately provisioned PostgreSQL target."""

from __future__ import annotations

import argparse
import json
import os

from sql_connectome.target_admission import (
    TargetAdmissionExpectation,
    admit_postgres_target,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect an existing PostgreSQL target; never provisions or activates it."
    )
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--target-key", required=True)
    parser.add_argument("--expected-provider-kind", required=True)
    parser.add_argument("--expected-provider-resource-ref", required=True)
    parser.add_argument("--expected-host", required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--expected-user", required=True)
    parser.add_argument("--expected-system-identifier", required=True)
    parser.add_argument("--expected-migration-version", required=True)
    parser.add_argument("--expected-migration-checksum", required=True)
    parser.add_argument("--expected-profile-digest", required=True)
    parser.add_argument("--expected-policy-digest", required=True)
    parser.add_argument("--project-scope", default="PROJECT_LANTERN")
    parser.add_argument("--expected-facade-id", default="BT2_MATERIAL_CUT_V1")
    parser.add_argument("--min-material-count", type=int, default=1)
    args = parser.parse_args()

    registry_dsn = os.getenv("SQL_CONNECTOME_DATABASE_URL")
    target_dsn = os.getenv("SQL_CONNECTOME_TARGET_DATABASE_URL")
    if not registry_dsn or not target_dsn:
        parser.error(
            "set SQL_CONNECTOME_DATABASE_URL and SQL_CONNECTOME_TARGET_DATABASE_URL "
            "in the operator environment; never pass credentials as CLI arguments"
        )

    expectation = TargetAdmissionExpectation(
        project_key=args.project_key,
        target_key=args.target_key,
        expected_provider_kind=args.expected_provider_kind,
        expected_provider_resource_ref=args.expected_provider_resource_ref,
        expected_host=args.expected_host,
        expected_database=args.expected_database,
        expected_user=args.expected_user,
        expected_system_identifier=args.expected_system_identifier,
        expected_migration_version=args.expected_migration_version,
        expected_migration_checksum=args.expected_migration_checksum,
        expected_profile_digest=args.expected_profile_digest,
        expected_policy_digest=args.expected_policy_digest,
        project_scope=args.project_scope,
        expected_facade_id=args.expected_facade_id,
        min_material_count=args.min_material_count,
    )
    result = admit_postgres_target(registry_dsn, target_dsn, expectation)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit({"PASS": 0, "FAIL": 2, "UNKNOWN": 3}[result["status"]])


if __name__ == "__main__":
    main()
