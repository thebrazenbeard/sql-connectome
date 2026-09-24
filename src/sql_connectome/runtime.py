from __future__ import annotations

import base64
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class RuntimeConfigurationError(RuntimeError):
    pass


def configure_database_environment(
    *,
    ca_path: Path = Path("/tmp/sql-connectome-project-ca.pem"),
) -> str:
    """Normalize managed-PostgreSQL environment variables.

    SQL Connectome remains provider-neutral. When a host injects a base64 project CA,
    this helper upgrades the injected PostgreSQL URI to certificate-verifying TLS.
    """

    database_url = os.getenv("SQL_CONNECTOME_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeConfigurationError("DATABASE_URL_MISSING")

    encoded_ca = os.getenv("PROJECT_CA_CERT")
    if not encoded_ca:
        os.environ["SQL_CONNECTOME_DATABASE_URL"] = database_url
        return database_url

    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise RuntimeConfigurationError("DATABASE_URL_MUST_BE_POSTGRES_URI")

    try:
        ca_bytes = base64.b64decode(encoded_ca, validate=True)
    except Exception as exc:
        raise RuntimeConfigurationError("PROJECT_CA_CERT_INVALID_BASE64") from exc

    if not ca_bytes:
        raise RuntimeConfigurationError("PROJECT_CA_CERT_EMPTY")

    ca_path.parent.mkdir(parents=True, exist_ok=True)
    ca_path.write_bytes(ca_bytes)
    ca_path.chmod(0o600)

    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"sslmode", "sslrootcert"}
    ]
    query.extend(
        [
            ("sslmode", "verify-full"),
            ("sslrootcert", str(ca_path)),
        ]
    )
    secure_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )
    os.environ["SQL_CONNECTOME_DATABASE_URL"] = secure_url
    return secure_url
