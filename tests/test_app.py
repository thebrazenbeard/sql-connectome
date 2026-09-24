from fastapi.testclient import TestClient

from sql_connectome.app import app


def test_public_healthz() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
