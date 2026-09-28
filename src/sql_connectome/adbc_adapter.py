from __future__ import annotations

from dataclasses import dataclass
from typing import Any\nfrom collections.abc import Callable

from .connectivity import ConnectionIdentity
from .dbapi_adapter import DBAPISession


@dataclass(frozen=True, slots=True)
class ADBCAdapter:
    provider: str
    engine: str
    engine_version: str | None
    transport_implementation: str
    transport_version: str | None
    connect: Callable[[], Any] | None = None
    catalog: str | None = None
    endpoint_identity: str | None = None
    session_facts: tuple[tuple[str, str], ...] = ()
    capabilities: tuple[str, ...] = ("execute",)

    @property
    def available(self) -> bool:
        return self.connect is not None

    def open_session(self) -> DBAPISession:
        if self.connect is None:
            raise RuntimeError(\n                "ADBC transport is unavailable; provide an explicit connection factory"\n            )
        connection = self.connect()
        identity = ConnectionIdentity(
            provider=self.provider,
            engine=self.engine,
            engine_version=self.engine_version,
            transport_family="adbc",
            transport_implementation=self.transport_implementation,
            transport_version=self.transport_version,
            endpoint_identity=self.endpoint_identity,
            catalog=self.catalog,
            session_facts=self.session_facts,
            capabilities=self.capabilities,
        )
        return DBAPISession(connection, identity)
