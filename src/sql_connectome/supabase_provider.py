from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


class SupabaseObservationError(ValueError):
    """Invalid or unsafe Supabase project observation."""


_SECRET_MARKERS = (
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "database_password",
    "password",
    "secret",
    "service_role",
    "token",
)


def _reject_secret_bearing_keys(value: Any, *, path: str = "project") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key).lower()
            if any(marker in key for marker in _SECRET_MARKERS):
                raise SupabaseObservationError(
                    "secret-bearing field is not admissible in provider observation: "
                    f"{path}.{raw_key}"
                )
            _reject_secret_bearing_keys(nested, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_secret_bearing_keys(nested, path=f"{path}[{index}]")


def _required_text(value: Mapping[str, Any], key: str, *, scope: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise SupabaseObservationError(f"{scope}.{key} must be non-empty text")
    return raw.strip()


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    raw = value.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise SupabaseObservationError(f"{key} must be non-empty text when present")
    return raw.strip()



def _safe_database_host(database: Mapping[str, Any]) -> str | None:
    host = _optional_text(database, "host")
    if host is None:
        return None
    if any(ch.isspace() or ord(ch) < 33 for ch in host) or any(
        char in host for char in ("/", "\\", "?", "#", "@")
    ):
        raise SupabaseObservationError("database host must be a bare hostname or host:port")
    try:
        parsed = urlsplit("//" + host)
        port = parsed.port
    except ValueError as exc:
        raise SupabaseObservationError("database host contains invalid port or IPv6 syntax") from exc
    if not parsed.hostname or parsed.username or parsed.password:
        raise SupabaseObservationError("database host contains unsupported authority components")
    if port is not None and port < 1:
        raise SupabaseObservationError("database host port must be positive")
    return host


def _lifecycle_state(provider_status: str) -> str:
    normalized = provider_status.strip().upper()
    if normalized == "ACTIVE_HEALTHY":
        return "RUNNING"
    if normalized in {"COMING_UP", "CREATING", "RESTORING", "UPGRADING"}:
        return "PROVISIONING"
    if normalized in {"PAUSED", "INACTIVE", "INACTIVE_HEALTHY"}:
        return "STOPPED"
    if normalized in {"DEGRADED", "UNHEALTHY", "ACTIVE_UNHEALTHY"}:
        return "DEGRADED"
    return "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SupabaseProjectObservation:
    ref: str
    name: str
    region: str
    provider_status: str
    postgres_engine: str
    database_version: str | None
    release_channel: str | None
    database_host: str | None

    @classmethod
    def from_management_project(
        cls,
        project: Mapping[str, Any],
    ) -> SupabaseProjectObservation:
        if not isinstance(project, Mapping):
            raise SupabaseObservationError("project observation must be an object")
        _reject_secret_bearing_keys(project)

        database = project.get("database")
        if not isinstance(database, Mapping):
            raise SupabaseObservationError("project.database must be an object")

        return cls(
            ref=_required_text(project, "ref", scope="project"),
            name=_required_text(project, "name", scope="project"),
            region=_required_text(project, "region", scope="project"),
            provider_status=_required_text(project, "status", scope="project"),
            postgres_engine=_required_text(database, "postgres_engine", scope="project.database"),
            database_version=_optional_text(database, "version"),
            release_channel=_optional_text(database, "release_channel"),
            database_host=_safe_database_host(database),
        )

    @property
    def lifecycle_state(self) -> str:
        return _lifecycle_state(self.provider_status)

    def registration_proposal(
        self,
        *,
        project_key: str,
        target_key: str = "primary",
        target_role: str = "PRIMARY",
        database_name: str = "postgres",
    ) -> dict[str, Any]:
        if not project_key.strip():
            raise SupabaseObservationError("project_key is required")
        if not target_key.strip():
            raise SupabaseObservationError("target_key is required")
        if not database_name.strip():
            raise SupabaseObservationError("database_name is required")

        metadata = {
            "observation_class": "SUPABASE_MANAGEMENT_PROJECT_OBSERVATION",
            "provider_project_name": self.name,
            "provider_status": self.provider_status,
            "postgres_engine": self.postgres_engine,
        }
        if self.database_version is not None:
            metadata["database_version"] = self.database_version
        if self.release_channel is not None:
            metadata["release_channel"] = self.release_channel
        if self.database_host is not None:
            metadata["database_host"] = self.database_host

        return {
            "project_key": project_key.strip(),
            "target_key": target_key.strip(),
            "target_role": target_role,
            "engine": "postgresql",
            "provider_kind": "supabase",
            "provider_resource_ref": self.ref,
            "database_name": database_name.strip(),
            "region": self.region,
            "lifecycle_state": self.lifecycle_state,
            "capabilities": {
                "managed_postgresql": True,
                "provider_observation_only": True,
            },
            "metadata": metadata,
        }