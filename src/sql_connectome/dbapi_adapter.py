from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sql_connectome.connectivity as connectivity

from .engine_validation import NativeEngineError
from .receipts import canonical_digest


_PROTECTED = {
    connectivity.EffectClass.MUTATING,
    connectivity.EffectClass.DDL,
    connectivity.EffectClass.TRANSACTION_CONTROL,
    connectivity.EffectClass.UNKNOWN,
}


@dataclass(slots=True)
class DBAPISession:
    connection: Any
    identity: connectivity.ConnectionIdentity

    def __enter__(self) -> DBAPISession:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.connection.close()

    def execute(
        self,
        sql: str,
        *,
        effect: connectivity.EffectClass,
        upstream_receipts: tuple[str, ...] = (),
        authorization_receipt: str | None = None,
    ) -> connectivity.ConnectivityExecutionResult:
        if effect in _PROTECTED and not authorization_receipt:
            raise connectivity.ProtectedEffectError(
                f"{effect.value} requires an external authorization receipt"
            )
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            description = cursor.description
            if description is None:
                rows = ()
                columns = ()
            else:
                rows = tuple(tuple(row) for row in cursor.fetchall())
                columns = tuple(str(item[0]) for item in description)
            error = None
        except Exception as exc:
            rows = None
            columns = ()
            error = NativeEngineError(type(exc).__name__, str(exc))
        return connectivity.ConnectivityExecutionResult(
            connection_identity_digest=connectivity.connection_identity_digest(self.identity),
            sql_digest=canonical_digest({"sql": sql}),
            effect=effect,
            rows=rows,
            columns=columns,
            native_error=error,
            upstream_receipts=upstream_receipts,
            authorization_receipt=authorization_receipt,
        )


@dataclass(frozen=True, slots=True)
class DBAPIAdapter:
    provider: str
    engine: str
    engine_version: str | None
    transport_implementation: str
    transport_version: str | None
    connect: Any
    catalog: str | None = None
    endpoint_identity: str | None = None
    session_facts: tuple[tuple[str, str], ...] = ()
    capabilities: tuple[str, ...] = ("execute",)

    def open_session(self) -> DBAPISession:
        connection = self.connect()
        identity = connectivity.ConnectionIdentity(
            provider=self.provider,
            engine=self.engine,
            engine_version=self.engine_version,
            transport_family="dbapi",
            transport_implementation=self.transport_implementation,
            transport_version=self.transport_version,
            endpoint_identity=self.endpoint_identity,
            catalog=self.catalog,
            session_facts=self.session_facts,
            capabilities=self.capabilities,
        )
        return DBAPISession(connection, identity)
