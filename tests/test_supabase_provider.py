import pytest

from sql_connectome.supabase_provider import (
    SupabaseObservationError,
    SupabaseProjectObservation,
)


def project(status: str = "ACTIVE_HEALTHY") -> dict:
    return {
        "id": "example-ref",
        "ref": "example-ref",
        "organization_id": "example-org",
        "name": "Example",
        "region": "us-east-2",
        "status": status,
        "database": {
            "host": "db.example-ref.supabase.co",
            "version": "17.6.1.166",
            "postgres_engine": "17",
            "release_channel": "ga",
        },
        "created_at": "2026-10-07T00:00:00Z",
    }


def test_supabase_observation_normalizes_management_project_without_secrets() -> None:
    observation = SupabaseProjectObservation.from_management_project(project())
    proposal = observation.registration_proposal(project_key="vera")

    assert proposal == {
        "project_key": "vera",
        "target_key": "primary",
        "target_role": "PRIMARY",
        "engine": "postgresql",
        "provider_kind": "supabase",
        "provider_resource_ref": "example-ref",
        "database_name": "postgres",
        "region": "us-east-2",
        "lifecycle_state": "RUNNING",
        "capabilities": {
            "managed_postgresql": True,
            "provider_observation_only": True,
        },
        "metadata": {
            "observation_class": "SUPABASE_MANAGEMENT_PROJECT_OBSERVATION",
            "provider_project_name": "Example",
            "provider_status": "ACTIVE_HEALTHY",
            "postgres_engine": "17",
            "database_version": "17.6.1.166",
            "release_channel": "ga",
            "database_host": "db.example-ref.supabase.co",
        },
    }
    rendered = repr(proposal).lower()
    assert "password" not in rendered
    assert "access_token" not in rendered
    assert "service_role" not in rendered


@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [
        ("ACTIVE_HEALTHY", "RUNNING"),
        ("RESTORING", "PROVISIONING"),
        ("PAUSED", "STOPPED"),
        ("ACTIVE_UNHEALTHY", "DEGRADED"),
        ("SOMETHING_NEW", "UNKNOWN"),
    ],
)
def test_supabase_status_mapping_fails_unknown_closed(
    provider_status: str,
    expected: str,
) -> None:
    observation = SupabaseProjectObservation.from_management_project(
        project(provider_status)
    )
    assert observation.lifecycle_state == expected


@pytest.mark.parametrize(
    "secret_patch",
    [
        {"access_token": "secret"},
        {"database": {"password": "secret"}},
        {"metadata": {"service_role_key": "secret"}},
    ],
)
def test_supabase_observation_rejects_secret_bearing_fields(
    secret_patch: dict,
) -> None:
    value = project()
    for key, patch in secret_patch.items():
        if isinstance(patch, dict) and isinstance(value.get(key), dict):
            value[key] = {**value[key], **patch}
        else:
            value[key] = patch

    with pytest.raises(SupabaseObservationError, match="secret-bearing"):
        SupabaseProjectObservation.from_management_project(value)


def test_supabase_observation_requires_management_identity_fields() -> None:
    value = project()
    value["ref"] = ""
    with pytest.raises(SupabaseObservationError, match=r"project\.ref"):
        SupabaseProjectObservation.from_management_project(value)


def test_registration_is_a_proposal_not_provider_effect() -> None:
    observation = SupabaseProjectObservation.from_management_project(project())
    proposal = observation.registration_proposal(project_key="vera", target_key="supabase-primary")

    assert proposal["capabilities"]["provider_observation_only"] is True
    assert set(proposal) == {
        "project_key",
        "target_key",
        "target_role",
        "engine",
        "provider_kind",
        "provider_resource_ref",
        "database_name",
        "region",
        "lifecycle_state",
        "capabilities",
        "metadata",
    }

@pytest.mark.parametrize(
    "host",
    [
        "postgresql://reporter:example-secret@db.example-ref.supabase.co:5432/postgres",
        "db.example-ref.supabase.co:example-secret",
        "db.example-ref.supabase.co/path",
        "db.example-ref.supabase.co\\npassword",
        "db.example-ref.supabase.co?token=example",
    ],
)
def test_supabase_observation_never_carries_credential_bearing_host_values(host: str) -> None:
    value = project()
    value["database"]["host"] = host
    with pytest.raises(SupabaseObservationError, match="database host"):
        SupabaseProjectObservation.from_management_project(value)
