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
    ("field", "value"),
    [
        ("name", "https://user:password@control.example/"),
        ("region", "us-east-2?access_token=secret"),
        ("database.host", "postgresql://user:password@db.example/"),
    ],
)
def test_supabase_observation_rejects_credential_like_values(field: str, value: str) -> None:
    data = project()
    if field.startswith("database."):
        data["database"][field.split(".", 1)[1]] = value
    else:
        data[field] = value
    with pytest.raises(SupabaseObservationError, match="credential-like") as error:
        SupabaseProjectObservation.from_management_project(data)
    assert "password@" not in str(error.value)
    assert "access_token=secret" not in str(error.value)


def test_registration_proposal_rejects_credentialed_operator_value() -> None:
    observation = SupabaseProjectObservation.from_management_project(project())
    with pytest.raises(SupabaseObservationError, match="credential-like"):
        observation.registration_proposal(project_key="postgresql://user:pass@host/database")


def test_direct_observation_constructor_cannot_bypass_value_guard() -> None:
    with pytest.raises(SupabaseObservationError, match="credential-like"):
        SupabaseProjectObservation(
            ref="valid-ref", name="Bearer plaintext-token", region="us-east-2",
            provider_status="ACTIVE_HEALTHY", postgres_engine="17",
            database_version=None, release_channel=None, database_host=None,
        )


@pytest.mark.parametrize("key, payload", [
    ("password=SENTINEL-SECRET-IN-KEY", "benign"),
    ("extra=SENTINEL-SECRET-IN-KEY", "https://user:pass@evil.invalid"),
])
def test_rejection_error_does_not_echo_untrusted_key_or_value(key: str, payload: str) -> None:
    data = project()
    data[key] = payload
    with pytest.raises(SupabaseObservationError) as error:
        SupabaseProjectObservation.from_management_project(data)
    assert "SENTINEL-SECRET-IN-KEY" not in str(error.value)
    assert "evil.invalid" not in str(error.value)


@pytest.mark.parametrize("bad_field", [None, b"opaque-credentials", 42])
def test_direct_constructor_rejects_untyped_required_fields(bad_field: object) -> None:
    with pytest.raises(SupabaseObservationError, match="required observation fields"):
        SupabaseProjectObservation(
            ref=bad_field, name="Example", region="us-east-2",
            provider_status="ACTIVE_HEALTHY", postgres_engine="17",
            database_version=None, release_channel=None, database_host=None,
        )


def test_registration_proposal_rejects_nonstring_operator_inputs() -> None:
    observation = SupabaseProjectObservation.from_management_project(project())
    with pytest.raises(SupabaseObservationError, match="registration fields must be text"):
        observation.registration_proposal(project_key=b"opaque-credentials")


@pytest.mark.parametrize("secret_text", [
    "Basic dXNlcjpwYXNz",
    "Authorization: Bearer secret",
    "Proxy-Authorization: Basic dXNlcjpwYXNz",
])
def test_observation_rejects_header_like_credentials_before_proposal(secret_text: str) -> None:
    data = project()
    data["name"] = secret_text
    with pytest.raises(SupabaseObservationError, match="credential-like") as error:
        SupabaseProjectObservation.from_management_project(data)
    assert secret_text not in str(error.value)


@pytest.mark.parametrize("unsafe", [
    "token = SENTINEL_PRIVATE_VALUE",
    "password : SENTINEL_PRIVATE_VALUE",
    "access_token : SENTINEL_PRIVATE_VALUE",
    "harmless" + chr(0x85) + "text",
])
def test_management_observation_rejects_spaced_secret_assignments_and_c1_controls(
    unsafe: str,
) -> None:
    data = project()
    data["name"] = unsafe
    with pytest.raises(SupabaseObservationError, match="credential-like") as error:
        SupabaseProjectObservation.from_management_project(data)
    assert "SENTINEL_PRIVATE_VALUE" not in str(error.value)


@pytest.mark.parametrize("unsafe", ["token = SENTINEL_PRIVATE_VALUE", "id" + chr(0x85) + "name"])
def test_direct_observation_rejects_unsafe_text(unsafe: str) -> None:
    with pytest.raises(SupabaseObservationError, match="credential-like"):
        SupabaseProjectObservation(
            ref="valid-ref", name=unsafe, region="us-east-2",
            provider_status="ACTIVE_HEALTHY", postgres_engine="17",
            database_version=None, release_channel=None, database_host=None,
        )


@pytest.mark.parametrize("unsafe", ["password : SENTINEL_PRIVATE_VALUE", "ops" + chr(0x85) + "key"])
def test_registration_proposal_rejects_unsafe_operator_values(unsafe: str) -> None:
    obs = SupabaseProjectObservation.from_management_project(project())
    with pytest.raises(SupabaseObservationError, match="credential-like"):
        obs.registration_proposal(project_key=unsafe)
