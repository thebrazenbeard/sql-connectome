from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

import sql_connectome.dbapi_adapter as dbapi_adapter
from sql_connectome.connectivity import (
    ConnectionIdentity,
    EffectClass,
    ProtectedEffectError,
    connection_identity_digest,
)
from sql_connectome.dbapi_adapter import DBAPIAdapter


def test_connection_identity_digest_binds_transport_and_session_without_secret() -> None:
    identity = ConnectionIdentity(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_family="dbapi",
        transport_implementation="sqlite3",
        transport_version=sqlite3.version,
        catalog=":memory:",
        session_facts=(("mode", "isolated"),),
    )
    payload = identity.as_dict()
    assert "password" not in str(payload).lower()
    assert connection_identity_digest(identity) == connection_identity_digest(identity)


@pytest.mark.parametrize("transport", ["dbapi", "adbc"])
def test_adapter_rejects_declared_engine_mismatching_native_driver(transport: str) -> None:
    """A caller cannot give an SQLite connection a PostgreSQL identity receipt."""
    from sql_connectome.adbc_adapter import ADBCAdapter

    class TrackedSQLite(sqlite3.Connection):
        closed = False

        def close(self) -> None:
            self.closed = True
            super().close()

    connection = sqlite3.connect(":memory:", factory=TrackedSQLite)
    adapter_type = DBAPIAdapter if transport == "dbapi" else ADBCAdapter
    adapter = adapter_type(
        provider="untrusted-declaration",
        engine="postgresql",
        engine_version="16",
        transport_implementation=f"{transport}-sqlite-driver",
        transport_version="1",
        connect=lambda: connection,
    )
    with pytest.raises(ProtectedEffectError, match="engine identity does not match native driver"):
        adapter.open_session()
    assert connection.closed


def test_session_rechecks_native_engine_if_identity_changes_after_open() -> None:
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version=sqlite3.version,
        connect=lambda: sqlite3.connect(":memory:"),
    )
    with adapter.open_session() as session:
        session.identity = ConnectionIdentity(
            provider="spoofed",
            engine="postgresql",
            engine_version="16",
            transport_family="dbapi",
            transport_implementation="sqlite3",
        )
        with pytest.raises(
            ProtectedEffectError, match="engine identity does not match native driver"
        ):
            session.execute("SELECT 1", effect=EffectClass.READ_ONLY)


def test_psycopg_driver_cannot_be_declared_sqlite_without_executing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePgConnection:
        closed = False

        def close(self) -> None:
            self.closed = True

    connection = FakePgConnection()
    monkeypatch.setattr(dbapi_adapter.psycopg, "Connection", FakePgConnection)
    adapter = DBAPIAdapter(
        provider="untrusted-declaration",
        engine="sqlite",
        engine_version="3",
        transport_implementation="psycopg",
        transport_version="3",
        connect=lambda: connection,
    )
    with pytest.raises(
        ProtectedEffectError, match="engine identity does not match native driver"
    ):
        adapter.open_session()
    assert connection.closed


def test_authorizer_cannot_relabel_identity_after_driver_binding() -> None:
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version="3",
        connect=lambda: sqlite3.connect(":memory:"),
    )
    with adapter.open_session() as session:
        original_identity = session.identity

        def mutate_identity(sql, effect, receipt, identity):
            session.identity = ConnectionIdentity(
                provider="spoofed",
                engine="postgresql",
                engine_version="16",
                transport_family="dbapi",
                transport_implementation="sqlite3",
            )
            return effect is EffectClass.DDL and receipt == "fixture:authorized"

        session.effect_authorizer = mutate_identity
        result = session.execute(
            "CREATE TABLE item(value TEXT)",
            effect=EffectClass.DDL,
            authorization_receipt="fixture:authorized",
        )
        assert result.native_error is None
        assert result.connection_identity_digest == connection_identity_digest(
            original_identity
        )


@pytest.mark.parametrize("mutation_target", ["callback", "session"])
def test_authorizer_cannot_mutate_frozen_identity_into_receipt(
    mutation_target: str,
) -> None:
    """Even object.__setattr__ must not relabel a committed SQLite effect."""
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version="3",
        connect=lambda: sqlite3.connect(":memory:"),
    )
    with adapter.open_session() as session:
        expected_digest = connection_identity_digest(session.identity)

        def hostile_authorizer(sql, effect, receipt, identity):
            target = identity if mutation_target == "callback" else session.identity
            object.__setattr__(target, "engine", "postgresql")
            return effect is EffectClass.DDL and receipt == "fixture:authorized"

        session.effect_authorizer = hostile_authorizer
        result = session.execute(
            "CREATE TABLE item(value TEXT)",
            effect=EffectClass.DDL,
            authorization_receipt="fixture:authorized",
        )
        assert result.native_error is None
        assert result.connection_identity_digest == expected_digest


def test_dbapi_read_only_execution_binds_identity_and_upstream_receipts() -> None:
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version=sqlite3.version,
        connect=lambda: sqlite3.connect(":memory:"),
        catalog=":memory:",
    )
    with adapter.open_session() as session:
        result = session.execute(
            "SELECT 1",
            effect=EffectClass.READ_ONLY,
            upstream_receipts=("validation:abc",),
        )
    assert result.rows == ((1,),)
    assert result.upstream_receipts == ("validation:abc",)
    assert result.connection_identity_digest


def test_protected_effect_requires_external_authorization_receipt() -> None:
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version=sqlite3.version,
        connect=lambda: sqlite3.connect(":memory:"),
        catalog=":memory:",
    )
    with adapter.open_session() as session:
        with pytest.raises(ProtectedEffectError):
            session.execute("CREATE TABLE t(a)", effect=EffectClass.DDL)
        with pytest.raises(ProtectedEffectError):
            session.execute(
                "CREATE TABLE t(a)",
                effect=EffectClass.DDL,
                authorization_receipt="authorization:explicit",
            )

    authorized_adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version=sqlite3.version,
        connect=lambda: sqlite3.connect(":memory:"),
        effect_authorizer=(
            lambda sql, effect, receipt, identity: (
                sql == "CREATE TABLE t(a)"
                and effect is EffectClass.DDL
                and receipt == "authorization:explicit"
                and identity.engine == "sqlite"
            )
        ),
    )
    with authorized_adapter.open_session() as session:
        with pytest.raises(ProtectedEffectError):
            session.execute(
                "CREATE TABLE t(a)",
                effect=EffectClass.DDL,
                authorization_receipt="authorization:arbitrary",
            )
        result = session.execute(
            "CREATE TABLE t(a)",
            effect=EffectClass.DDL,
            authorization_receipt="authorization:explicit",
        )
    assert result.authorization_receipt == "authorization:explicit"
    assert result.native_error is None


def test_authorized_write_is_committed_before_success_receipt(tmp_path: Path) -> None:
    # The file-backed database distinguishes cursor success from durable commit.
    database_path = tmp_path / "persist.sqlite"

    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version="3",
        connect=lambda: sqlite3.connect(database_path),
        effect_authorizer=lambda sql, effect, receipt, identity: (
            receipt == "external:verified-for-test"
            and effect in (EffectClass.DDL, EffectClass.MUTATING)
            and identity.engine == "sqlite"
        ),
    )
    with adapter.open_session() as session:
        created = session.execute(
            "CREATE TABLE item(value TEXT)",
            effect=EffectClass.DDL,
            authorization_receipt="external:verified-for-test",
        )
        inserted = session.execute(
            "INSERT INTO item(value) VALUES ('persisted')",
            effect=EffectClass.MUTATING,
            authorization_receipt="external:verified-for-test",
        )
        assert created.native_error is None
        assert inserted.native_error is None

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT value FROM item").fetchall() == [("persisted",)]


def test_unverified_transaction_control_and_unknown_remain_denied() -> None:
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version="3",
        connect=lambda: sqlite3.connect(":memory:"),
        effect_authorizer=lambda *_: True,
    )
    with adapter.open_session() as session:
        for effect in (EffectClass.TRANSACTION_CONTROL, EffectClass.UNKNOWN):
            with pytest.raises(ProtectedEffectError, match="cannot be executed"):
                session.execute("COMMIT", effect=effect, authorization_receipt="allowed")


def test_commit_failure_is_native_error_without_false_write_success(tmp_path: Path) -> None:
    database_path = tmp_path / "failed_commit.sqlite"
    with sqlite3.connect(database_path) as setup:
        setup.execute("CREATE TABLE item(value TEXT)")

    class FailedCommitConnection(sqlite3.Connection):
        def commit(self) -> None:
            raise sqlite3.OperationalError("inert commit failure")

    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version="3",
        connect=lambda: sqlite3.connect(database_path, factory=FailedCommitConnection),
        effect_authorizer=lambda *_: True,
    )
    with adapter.open_session() as session:
        result = session.execute(
            "INSERT INTO item(value) VALUES ('rolled-back')",
            effect=EffectClass.MUTATING,
            authorization_receipt="external:verified-for-test",
        )
        assert result.native_error is not None
        assert result.native_error.error_class == "OperationalError"
        assert result.rows is None

    with sqlite3.connect(database_path) as check:
        assert check.execute("SELECT COUNT(*) FROM item").fetchone() == (0,)


def test_claimed_read_only_mutation_is_rejected_without_driver_execution() -> None:
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version=sqlite3.version,
        connect=lambda: sqlite3.connect(":memory:"),
    )
    with adapter.open_session() as session:
        with pytest.raises(ProtectedEffectError, match="one SELECT"):
            session.execute("CREATE TABLE forbidden(a)", effect=EffectClass.READ_ONLY)
        assert session.connection.execute(
            "SELECT name FROM sqlite_master WHERE name='forbidden'"
        ).fetchall() == []
        result = session.execute("SELECT 1", effect=EffectClass.READ_ONLY)
        assert result.rows == ((1,),)
        assert session.connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            session.connection.execute("CREATE TABLE forbidden(a)")


def test_read_only_unqualified_driver_fails_closed() -> None:
    class FakeConnection:
        def cursor(self) -> None:
            raise AssertionError("driver must never execute")

        def close(self) -> None:
            pass

    adapter = DBAPIAdapter(
        provider="unknown",
        engine="unknown",
        engine_version=None,
        transport_implementation="unknown",
        transport_version=None,
        connect=FakeConnection,
    )
    with adapter.open_session() as session:
        with pytest.raises(ProtectedEffectError, match="unqualified"):
            session.execute("SELECT 1", effect=EffectClass.READ_ONLY)


@pytest.mark.parametrize("transaction_idle", [True, False])
def test_psycopg_read_only_requires_idle_and_sets_native_boundary(
    monkeypatch: pytest.MonkeyPatch, transaction_idle: bool
) -> None:
    class PgCursor:
        description = (("value",),)

        def __init__(self, connection: PgConnection) -> None:
            self.connection = connection

        def execute(self, sql: str) -> None:
            assert self.connection.read_only is True
            assert sql == "SELECT 1"
            self.connection.info.transaction_status = psycopg.pq.TransactionStatus.INTRANS

        def fetchall(self) -> list[tuple[int]]:
            return [(1,)]

    class PgConnection:
        def __init__(self) -> None:
            status = (
                psycopg.pq.TransactionStatus.IDLE
                if transaction_idle
                else psycopg.pq.TransactionStatus.INTRANS
            )
            self.info = SimpleNamespace(transaction_status=status)
            self.read_only = False
            self.cursor_calls = 0
            self.rollback_calls = 0

        def cursor(self) -> PgCursor:
            self.cursor_calls += 1
            return PgCursor(self)

        def close(self) -> None:
            pass

        def rollback(self) -> None:
            self.rollback_calls += 1
            self.info.transaction_status = psycopg.pq.TransactionStatus.IDLE

    monkeypatch.setattr(dbapi_adapter.psycopg, "Connection", PgConnection)
    connection = PgConnection()
    adapter = DBAPIAdapter(
        provider="postgresql",
        engine="postgresql",
        engine_version="16",
        transport_implementation="psycopg",
        transport_version="3",
        connect=lambda: connection,
    )
    with adapter.open_session() as session:
        if transaction_idle:
            assert session.execute("SELECT 1", effect=EffectClass.READ_ONLY).rows == ((1,),)
            assert session.execute("SELECT 1", effect=EffectClass.READ_ONLY).rows == ((1,),)
            assert connection.cursor_calls == 2
            assert connection.rollback_calls == 2
        else:
            with pytest.raises(ProtectedEffectError, match="idle"):
                session.execute("SELECT 1", effect=EffectClass.READ_ONLY)
            assert connection.cursor_calls == 0


def test_native_execution_error_is_preserved() -> None:
    adapter = DBAPIAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="sqlite3",
        transport_version=sqlite3.version,
        connect=lambda: sqlite3.connect(":memory:"),
        catalog=":memory:",
    )
    with adapter.open_session() as session:
        result = session.execute("SELECT missing", effect=EffectClass.READ_ONLY)
    assert result.native_error is not None
    assert result.rows is None


def test_adbc_is_optional_and_factory_injected() -> None:
    from sql_connectome.adbc_adapter import ADBCAdapter

    unavailable = ADBCAdapter(
        provider="example",
        engine="example",
        engine_version=None,
        transport_implementation="adbc-example",
        transport_version=None,
    )
    assert unavailable.available is False
    with pytest.raises(RuntimeError):
        unavailable.open_session()

    available = ADBCAdapter(
        provider="sqlite",
        engine="sqlite",
        engine_version=sqlite3.sqlite_version,
        transport_implementation="adbc-test-double",
        transport_version="1",
        connect=lambda: sqlite3.connect(":memory:"),
    )
    with available.open_session() as session:
        result = session.execute("SELECT 1", effect=EffectClass.READ_ONLY)
        assert session.identity.transport_family == "adbc"
        assert result.rows == ((1,),)
