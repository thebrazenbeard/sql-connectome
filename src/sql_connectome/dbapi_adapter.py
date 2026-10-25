from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import psycopg

import sql_connectome.connectivity as connectivity

from .engine_validation import NativeEngineError
from .receipts import canonical_digest
from .sql_guard import SQLRejected, validate_readonly_sql

_AUTHORIZED_SQL_EFFECTS = {
    connectivity.EffectClass.MUTATING,
    connectivity.EffectClass.DDL,
}

EffectAuthorizer = Callable[
    [str, connectivity.EffectClass, str, connectivity.ConnectionIdentity], bool
]


@dataclass(slots=True)
class DBAPISession:
    connection: Any
    identity: connectivity.ConnectionIdentity
    effect_authorizer: EffectAuthorizer | None = None

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
        if not isinstance(effect, connectivity.EffectClass):
            raise connectivity.ProtectedEffectError("unrecognized SQL effect classification")
        if effect is connectivity.EffectClass.READ_ONLY:
            # The caller-supplied classification is evidence, not authority. Reject
            # mutating SQL before the driver sees it and also enforce a native DB
            # transaction boundary. An arbitrary DB-API driver is not presumed safe.
            try:
                validate_readonly_sql(sql)
            except SQLRejected as exc:
                raise connectivity.ProtectedEffectError("READ_ONLY requires one SELECT") from exc
            if isinstance(self.connection, sqlite3.Connection):
                if self.connection.in_transaction:
                    raise connectivity.ProtectedEffectError(
                        "READ_ONLY requires an idle SQLite transaction"
                    )
                self.connection.execute("PRAGMA query_only = ON")
            elif isinstance(self.connection, psycopg.Connection):
                if self.connection.info.transaction_status is not psycopg.pq.TransactionStatus.IDLE:
                    raise connectivity.ProtectedEffectError(
                        "READ_ONLY requires an idle PostgreSQL transaction"
                    )
                self.connection.read_only = True
            else:
                raise connectivity.ProtectedEffectError(
                    "READ_ONLY unsupported for this unqualified DB-API driver"
                )
        elif effect in _AUTHORIZED_SQL_EFFECTS:
            if not authorization_receipt or self.effect_authorizer is None:
                raise connectivity.ProtectedEffectError(
                    f"{effect.value} requires an independently verified authorization receipt"
                )
            if not self.effect_authorizer(sql, effect, authorization_receipt, self.identity):
                raise connectivity.ProtectedEffectError(
                    f"{effect.value} authorization receipt verification failed"
                )
            if isinstance(self.connection, sqlite3.Connection):
                if (
                    self.connection.in_transaction
                    or self.connection.execute("PRAGMA query_only").fetchone()[0]
                ):
                    raise connectivity.ProtectedEffectError(
                        "protected execution requires an idle, writable SQLite session"
                    )
            elif isinstance(self.connection, psycopg.Connection):
                if (
                    self.connection.info.transaction_status
                    is not psycopg.pq.TransactionStatus.IDLE
                    or self.connection.read_only
                ):
                    raise connectivity.ProtectedEffectError(
                        "protected execution requires an idle, writable PostgreSQL session"
                    )
            else:
                raise connectivity.ProtectedEffectError(
                    "protected execution unsupported for this unqualified DB-API driver"
                )
        else:
            raise connectivity.ProtectedEffectError(
                f"{effect.value} cannot be executed through the DB-API effect adapter"
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
            if effect is connectivity.EffectClass.READ_ONLY:
                # PostgreSQL SELECT normally opens a transaction. End it so a
                # second read can establish an equally explicit fresh boundary.
                self.connection.rollback()
            else:
                # A successful cursor.execute is not a durable write result.
                # The receipt may report success only after commit returns.
                self.connection.commit()
            error = None
        except Exception as exc:
            try:
                self.connection.rollback()
            except Exception as rollback_exc:
                exc = RuntimeError(f"{exc}; rollback failed: {rollback_exc}")
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
    effect_authorizer: EffectAuthorizer | None = None

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
        return DBAPISession(connection, identity, self.effect_authorizer)
