"""Local-only registration validation; these tests must not contact PostgreSQL."""

import pytest

from sql_connectome import projects


@pytest.fixture(autouse=True)
def forbid_database_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("validation must fail before opening a database connection")

    monkeypatch.setattr(projects.psycopg, "connect", _forbidden_connect)


@pytest.mark.parametrize(
    "metadata",
    [
        {"password": "plaintext-secret"},
        {"clientSecret": "plaintext-secret"},
        {"secret_key": "plaintext-secret"},
        {"client_secret_key": "plaintext-secret"},
        {"app_token": "plaintext-secret"},
        {"my_token": "plaintext-secret"},
        {"clientSecretKey": "plaintext-secret"},
        {"password_hash": "plaintext-secret"},
        {"nested": [{"authentication": {"access_token": "plaintext-secret"}}]},
        {"authorizationHeader": "plaintext-secret"},
        {"tlsPassword": "plaintext-secret"},
        {"session": {"cookie": "plaintext-secret"}},
        {"private-key-pem": "plaintext-secret"},
        {"uri": "postgresql://db.example.test/data"},
        {"endpoint": "postgresql+psycopg://db.example.test/data"},
        {"reference": "host=db.example.test user=app password=plaintext-secret"},
        {"reference": "host=db.example.test dbname=app"},
        {"connection": "https://user:pass@host.example.test/app"},
        {"endpoint": "https://host.example.test/app?api_key=plaintext-secret"},
        {"endpoint": "https://host.example.test/app?X-Amz-Signature=plaintext-secret"},
        {"endpoint": "https://host.example.test/app#access_token=plaintext-secret"},
        {"endpoint": "https://host.example.test/app#route?api_key=plaintext-secret"},
        {"reference": "Bearer plaintext-secret"},
        {"reference": "-----BEGIN PRIVATE KEY-----\nplaintext-secret\n-----END PRIVATE KEY-----"},
    ],
)
def test_project_rejects_secret_bearing_metadata_before_writing(
    metadata: dict[str, object],
) -> None:
    with pytest.raises(projects.ProjectRegistryError, match="CONTROL_PLANE_SECRETS_NOT_ALLOWED"):
        projects.register_project(
            "unused-no-connection",
            project_key="test-project",
            display_name="Test",
            metadata=metadata,
        )


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("metadata", {"deep": [{"refreshToken": "plaintext-secret"}]}),
        ("capabilities", {"apiKey": "plaintext-secret"}),
        ("provider_resource_ref", "postgresql://user:password@db.example.test/app"),
    ],
)
def test_target_rejects_secret_bearing_fields_before_writing(
    field_name: str, field_value: object
) -> None:
    kwargs = {field_name: field_value}
    with pytest.raises(projects.ProjectRegistryError, match="CONTROL_PLANE_SECRETS_NOT_ALLOWED"):
        projects.register_database_target(
            "unused-no-connection",
            project_key="test-project",
            target_key="primary",
            provider_kind="external-postgresql",
            database_name="app",
            **kwargs,
        )


@pytest.mark.parametrize(
    "metadata",
    [
        {"details": ({"service_role_key": "plaintext-secret"},)},
        {"nested": [({"accessToken": "plaintext-secret"},)]},
    ],
)
def test_project_rejects_secret_inside_json_serializable_tuple_before_writing(
    metadata: dict[str, object],
) -> None:
    with pytest.raises(projects.ProjectRegistryError, match="CONTROL_PLANE_SECRETS_NOT_ALLOWED"):
        projects.register_project(
            "unused-no-connection",
            project_key="test-project",
            display_name="Test",
            metadata=metadata,
        )


def test_target_rejects_secret_inside_json_serializable_tuple_before_writing() -> None:
    with pytest.raises(projects.ProjectRegistryError, match="CONTROL_PLANE_SECRETS_NOT_ALLOWED"):
        projects.register_database_target(
            "unused-no-connection",
            project_key="test-project",
            target_key="primary",
            provider_kind="external-postgresql",
            database_name="app",
            capabilities={"nested": ({"password": "plaintext-secret"},)},
        )


@pytest.mark.parametrize(
    "metadata",
    [
        {"purpose": "qualification", "token_count": 3},
        {"api_version": "v1", "resource": "pg-project-id", "region": "us-east-1"},
        {"nested": [None, {"read": True, "write": False}, 42]},
        {"nested": ("public", {"read": True})},
        {"documentation": "https://example.test/docs?version=1"},
        {"secretary_name": "Jane"},
    ],
)
def test_nonsecret_metadata_remains_valid(metadata: dict[str, object]) -> None:
    # The helper is intentionally exercised independently of any operator DB.
    projects._validate_nonsecret_metadata(metadata)


def test_error_does_not_echo_secret_value() -> None:
    secret_value = "known-secret-should-never-be-logged"
    with pytest.raises(projects.ProjectRegistryError) as exc:
        projects.register_project(
            "unused-no-connection",
            project_key="test-project",
            display_name="Test",
            metadata={"api_key": secret_value},
        )
    assert secret_value not in str(exc.value)


def test_malformed_url_fails_with_bounded_registry_error() -> None:
    with pytest.raises(projects.ProjectRegistryError, match="CONTROL_PLANE_METADATA_INVALID"):
        projects.register_project(
            "unused-no-connection",
            project_key="test-project",
            display_name="Test",
            metadata={"endpoint": "https://["},
        )
