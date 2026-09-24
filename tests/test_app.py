from fastapi.testclient import TestClient

from sql_connectome.app import app
from sql_connectome.config import get_settings


def test_public_healthz() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def _authenticated_client(monkeypatch) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setenv("SQL_CONNECTOME_DATABASE_URL", "postgresql://unused:unused@localhost/unused")
    monkeypatch.setenv("SQL_CONNECTOME_API_TOKEN", "semantic-test-token")
    get_settings.cache_clear()
    return TestClient(app), {"Authorization": "Bearer semantic-test-token"}


def test_connectome_dialect_inventory_requires_auth(monkeypatch) -> None:
    client, _ = _authenticated_client(monkeypatch)
    response = client.get("/v1/connectome/dialects")
    assert response.status_code == 401


def test_connectome_dialect_inventory(monkeypatch) -> None:
    client, headers = _authenticated_client(monkeypatch)
    response = client.get("/v1/connectome/dialects", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 9
    assert "postgresql" in {dialect["dialect_id"] for dialect in payload["dialects"]}


def test_connectome_translation_plan(monkeypatch) -> None:
    client, headers = _authenticated_client(monkeypatch)
    response = client.post(
        "/v1/connectome/translation-plan",
        headers=headers,
        json={
            "source_dialect": "bigquery",
            "target_dialect": "postgresql",
            "required_capabilities": ["relational_select", "window_functions", "qualify"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fidelity"] == "CONSTRUCTIVE"
    assert payload["missing_capabilities"] == ["qualify"]
    assert payload["unresolved_capabilities"] == []


def test_connectome_translation_plan_fails_closed(monkeypatch) -> None:
    client, headers = _authenticated_client(monkeypatch)
    response = client.post(
        "/v1/connectome/translation-plan",
        headers=headers,
        json={
            "source_dialect": "snowflake",
            "target_dialect": "sqlite",
            "required_capabilities": ["geospatial"],
        },
    )

    assert response.status_code == 200
    assert response.json()["fidelity"] == "UNREPRESENTABLE"


def test_connectome_probe_endpoint(monkeypatch) -> None:
    client, headers = _authenticated_client(monkeypatch)
    response = client.post(
        "/v1/connectome/probe",
        headers=headers,
        json={"sql": "SELECT TOP 5 * FROM users", "max_candidates": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["identity_proof"] is False
    assert payload["candidates"][0]["dialect_id"] == "tsql"


def test_connectome_bind_endpoint(monkeypatch) -> None:
    client, headers = _authenticated_client(monkeypatch)
    response = client.post(
        "/v1/connectome/bind",
        headers=headers,
        json={
            "sql": "SELECT id FROM users",
            "dialect": "postgresql",
            "schema_context": {"users": {"id": "INT"}},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["binding"]["status"] == "STATIC_BOUND"
    assert payload["binding"]["engine_validation"] == "NOT_RUN"


def test_connectome_postgresql_qualification_endpoint(monkeypatch) -> None:
    from sql_connectome import app as app_module

    def fake_qualification(settings, sql, source_dialect, *, allow_lossy=False):
        assert settings.api_token.get_secret_value() == "semantic-test-token"
        assert sql == "SELECT 1"
        assert source_dialect == "mysql"
        assert allow_lossy is False
        return {
            "schema": "SQL_CONNECTOME_TRANSLATION_QUALIFICATION_V1",
            "qualification": {"status": "PASS"},
        }

    monkeypatch.setattr(
        app_module,
        "qualify_translation_to_postgresql",
        fake_qualification,
    )
    client, headers = _authenticated_client(monkeypatch)
    response = client.post(
        "/v1/connectome/qualify/postgresql",
        headers=headers,
        json={
            "sql": "SELECT 1",
            "source_dialect": "mysql",
        },
    )

    assert response.status_code == 200
    assert response.json()["qualification"]["status"] == "PASS"


def test_connectome_contracts_endpoint(monkeypatch) -> None:
    client, headers = _authenticated_client(monkeypatch)
    response = client.post(
        "/v1/connectome/contracts",
        headers=headers,
        json={
            "sql": "SELECT LENGTH(name) FROM users",
            "dialect": "postgresql",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "SQL_CONNECTOME_EXPRESSION_CONTRACTS_V1"
    names = {row["name"] for row in payload["expression_contracts"]}
    assert "LENGTH" in names
