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
