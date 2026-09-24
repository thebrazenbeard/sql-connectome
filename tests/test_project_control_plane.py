import os

import psycopg
import pytest

from sql_connectome.config import Settings
from sql_connectome.projects import (
    ProjectRegistryError,
    list_projects,
    project_detail,
    register_database_target,
    register_project,
)

DSN = os.getenv("SQL_CONNECTOME_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DSN, reason="SQL_CONNECTOME_DATABASE_URL not set")


def settings() -> Settings:
    assert DSN
    return Settings(database_url=DSN, api_token="project-test-token")


def test_project_and_target_registration_roundtrip() -> None:
    assert DSN

    project = register_project(
        DSN,
        project_key="integration-project",
        display_name="Integration Project",
        metadata={"purpose": "qualification"},
    )
    assert project["state"] == "REGISTERED"

    replay = register_project(
        DSN,
        project_key="integration-project",
        display_name="Integration Project",
        metadata={"purpose": "qualification"},
    )
    assert replay["state"] == "ALREADY_REGISTERED"
    assert replay["project"]["project_id"] == project["project"]["project_id"]

    target = register_database_target(
        DSN,
        project_key="integration-project",
        target_key="primary",
        provider_kind="external-postgresql",
        provider_resource_ref="qualification-primary",
        database_name="sql_connectome",
        lifecycle_state="RUNNING",
        capabilities={"read": True, "write": False},
    )
    assert target["state"] == "REGISTERED"
    assert target["target"]["target_role"] == "PRIMARY"

    target_replay = register_database_target(
        DSN,
        project_key="integration-project",
        target_key="primary",
        provider_kind="external-postgresql",
        provider_resource_ref="qualification-primary",
        database_name="sql_connectome",
        lifecycle_state="RUNNING",
        capabilities={"read": True, "write": False},
    )
    assert target_replay["state"] == "ALREADY_REGISTERED"

    listing = list_projects(settings())
    assert listing["runtime"]["identity_digest"]
    assert "integration-project" in {
        item["project_key"] for item in listing["projects"]
    }

    detail = project_detail(settings(), "integration-project")
    assert detail["runtime"]["identity_digest"]
    assert detail["project"]["display_name"] == "Integration Project"
    assert [row["target_key"] for row in detail["targets"]] == ["primary"]


def test_project_key_conflict_fails_closed() -> None:
    assert DSN

    register_project(
        DSN,
        project_key="conflict-project",
        display_name="Original Name",
    )
    with pytest.raises(ProjectRegistryError, match="PROJECT_KEY_CONFLICT"):
        register_project(
            DSN,
            project_key="conflict-project",
            display_name="Different Name",
        )


def test_second_live_primary_is_rejected() -> None:
    assert DSN

    register_project(
        DSN,
        project_key="primary-project",
        display_name="Primary Project",
    )
    register_database_target(
        DSN,
        project_key="primary-project",
        target_key="first-primary",
        provider_kind="external-postgresql",
        database_name="first",
        target_role="PRIMARY",
    )

    with pytest.raises(psycopg.errors.UniqueViolation):
        register_database_target(
            DSN,
            project_key="primary-project",
            target_key="other-primary",
            provider_kind="other-provider",
            database_name="other",
            target_role="PRIMARY",
        )


def test_effect_receipts_are_append_only() -> None:
    assert DSN

    registered = register_project(
        DSN,
        project_key="receipt-project",
        display_name="Receipt Project",
    )
    receipt_id = registered["receipt"]["receipt_id"]

    with psycopg.connect(DSN) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="ARE_APPEND_ONLY"):
            conn.execute(
                """
                UPDATE sql_connectome.effect_receipts
                SET result = '{}'::jsonb
                WHERE receipt_id = %s
                """,
                (receipt_id,),
            )


def test_project_detail_missing_fails_closed() -> None:
    with pytest.raises(ProjectRegistryError, match="PROJECT_NOT_FOUND"):
        project_detail(settings(), "definitely-missing")
