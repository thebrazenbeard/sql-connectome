import base64
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from sql_connectome.runtime import RuntimeConfigurationError, configure_database_environment


def test_database_environment_passthrough_without_project_ca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROJECT_CA_CERT", raising=False)
    monkeypatch.delenv("SQL_CONNECTOME_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@db.example.test:5432/app?sslmode=require",
    )

    result = configure_database_environment()

    assert result.endswith("sslmode=require")
    assert os.environ["SQL_CONNECTOME_DATABASE_URL"] == result


def test_project_ca_upgrades_connection_to_verify_full(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ca_bytes = b"-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"
    ca_path = tmp_path / "project-ca.pem"
    monkeypatch.setenv(
        "SQL_CONNECTOME_DATABASE_URL",
        "postgresql://user:secret@db.example.test:5432/app?sslmode=require&application_name=test",
    )
    monkeypatch.setenv("PROJECT_CA_CERT", base64.b64encode(ca_bytes).decode("ascii"))

    result = configure_database_environment(ca_path=ca_path)
    parsed = urlsplit(result)
    query = parse_qs(parsed.query)

    assert parsed.hostname == "db.example.test"
    assert query["sslmode"] == ["verify-full"]
    assert query["sslrootcert"] == [str(ca_path)]
    assert query["application_name"] == ["test"]
    assert ca_path.read_bytes() == ca_bytes
    assert ca_path.stat().st_mode & 0o777 == 0o600


def test_invalid_project_ca_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "SQL_CONNECTOME_DATABASE_URL",
        "postgresql://user:secret@db.example.test:5432/app?sslmode=require",
    )
    monkeypatch.setenv("PROJECT_CA_CERT", "not-base64!")

    with pytest.raises(RuntimeConfigurationError, match="PROJECT_CA_CERT_INVALID_BASE64"):
        configure_database_environment(ca_path=tmp_path / "ca.pem")


def test_missing_database_url_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SQL_CONNECTOME_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeConfigurationError, match="DATABASE_URL_MISSING"):
        configure_database_environment()
