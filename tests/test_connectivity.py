import sqlite3

import pytest

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
        result = session.execute(
            "CREATE TABLE t(a)",
            effect=EffectClass.DDL,
            authorization_receipt="authorization:explicit",
        )
    assert result.authorization_receipt == "authorization:explicit"


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
