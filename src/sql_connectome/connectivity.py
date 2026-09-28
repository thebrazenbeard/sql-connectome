from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from .engine_validation import NativeEngineError
from .receipts import canonical_digest


class EffectClass(StrEnum):
    READ_ONLY = "READ_ONLY"
    MUTATING = "MUTATING"
    DDL = "DDL"
    TRANSACTION_CONTROL = "TRANSACTION_CONTROL"
    UNKNOWN = "UNKNOWN"


class ProtectedEffectError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class ConnectionIdentity:
    provider: str
    engine: str
    engine_version: str | None
    transport_family: str
    transport_implementation: str
    transport_version: str | None = None
    endpoint_identity: str | None = None
    catalog: str | None = None
    session_facts: tuple[tuple[str, str], ...] = ()
    capabilities: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_CONNECTION_IDENTITY_V1",
            "provider": self.provider,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "transport_family": self.transport_family,
            "transport_implementation": self.transport_implementation,
            "transport_version": self.transport_version,
            "endpoint_identity": self.endpoint_identity,
            "catalog": self.catalog,
            "session_facts": dict(sorted(self.session_facts)),
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True, slots=True)
class ConnectivityExecutionResult:
    connection_identity_digest: str
    sql_digest: str
    effect: EffectClass
    rows: tuple[tuple[Any, ...], ...] | None = None
    columns: tuple[str, ...] = ()
    native_error: NativeEngineError | None = None
    upstream_receipts: tuple[str, ...] = ()
    authorization_receipt: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_CONNECTIVITY_EXECUTION_V1",
            "connection_identity_digest": self.connection_identity_digest,
            "sql_digest": self.sql_digest,
            "effect": self.effect.value,
            "rows": [list(row) for row in self.rows] if self.rows is not None else None,
            "columns": list(self.columns),
            "native_error": self.native_error.as_dict() if self.native_error else None,
            "upstream_receipts": list(self.upstream_receipts),
            "authorization_receipt": self.authorization_receipt,
        }


class ConnectionSession(Protocol):
    @property
    def identity(self) -> ConnectionIdentity: ...

    def execute(
        self,
        sql: str,
        *,
        effect: EffectClass,
        upstream_receipts: tuple[str, ...] = (),
        authorization_receipt: str | None = None,
    ) -> ConnectivityExecutionResult: ...


def connection_identity_digest(identity: ConnectionIdentity) -> str:
    return canonical_digest(identity.as_dict())


def connectivity_execution_digest(result: ConnectivityExecutionResult) -> str:
    return canonical_digest(result.as_dict())
