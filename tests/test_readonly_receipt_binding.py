from contextlib import nullcontext
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from ipaddress import ip_address, ip_interface, ip_network
from types import SimpleNamespace
from uuid import UUID

import pytest
from psycopg.types.multirange import Multirange
from psycopg.types.range import Range

from sql_connectome import db
from sql_connectome.config import Settings
from sql_connectome.receipts import TYPED_PAYLOAD_DIGEST_FORMAT, typed_payload_digest


class _Cursor:
    def __init__(self, rows, column="value"):
        self.rows = rows
        self.description = (SimpleNamespace(name=column),)

    def fetchmany(self, count):
        return self.rows[:count]


class _Connection:
    def __init__(self, rows, column="value"):
        self.rows = rows
        self.column = column

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def transaction(self):
        return nullcontext()

    def execute(self, sql, params=None):
        if sql == "SELECT %s AS value":
            return _Cursor(self.rows, self.column)
        return None


def test_read_receipt_binds_parameters_and_actual_rows_without_echoing_raw_values(monkeypatch):
    settings = Settings(database_url="postgresql://offline/offline", api_token="test-token")
    monkeypatch.setattr(db, "_runtime_identity", lambda conn: {"identity_digest": "a" * 64})
    observed = {"result": "private-result-a"}
    monkeypatch.setattr(
        db, "connect", lambda settings: _Connection([{"value": observed["result"]}])
    )

    first = db.query_readonly(settings, "SELECT %s AS value", ["private-parameter-a"])
    observed["result"] = "private-result-b"
    changed_rows = db.query_readonly(settings, "SELECT %s AS value", ["private-parameter-a"])
    observed["result"] = "private-result-a"
    changed_parameter = db.query_readonly(settings, "SELECT %s AS value", ["private-parameter-b"])

    subjects = [result["receipt"]["subject"] for result in (first, changed_rows, changed_parameter)]
    assert subjects[0] != subjects[1]
    assert subjects[0] != subjects[2]
    assert subjects[0]["payload_digest_format"] == TYPED_PAYLOAD_DIGEST_FORMAT
    repeated = db.query_readonly(settings, "SELECT %s AS value", ["private-parameter-a"])
    assert subjects[0] == repeated["receipt"]["subject"]
    assert "private-parameter-a" not in str(subjects)
    assert "private-result-a" not in str(subjects)


def test_read_receipt_binds_column_names_and_truncation(monkeypatch):
    settings = Settings(
        database_url="postgresql://offline/offline", api_token="test-token", max_rows=1
    )
    monkeypatch.setattr(db, "_runtime_identity", lambda conn: {"identity_digest": "a" * 64})
    observed = {"column": "value", "rows": [{"value": b"\x00\xff"}]}
    monkeypatch.setattr(
        db, "connect", lambda settings: _Connection(observed["rows"], observed["column"])
    )

    first = db.query_readonly(settings, "SELECT %s AS value", [1])
    observed["column"] = "other"
    changed_columns = db.query_readonly(settings, "SELECT %s AS value", [1])
    observed["column"] = "value"
    observed["rows"] = [{"value": b"\x00\xff"}, {"value": b"not exposed"}]
    truncated = db.query_readonly(settings, "SELECT %s AS value", [1])

    first_digest = first["receipt"]["subject"]["result_digest"]
    assert first_digest != changed_columns["receipt"]["subject"]["result_digest"]
    assert first_digest == truncated["receipt"]["subject"]["result_digest"]
    assert first["receipt"]["subject"]["truncated"] is False
    assert truncated["receipt"]["subject"]["truncated"] is True
    assert truncated["rows"] == [{"value": b"\x00\xff"}]


def test_typed_digest_does_not_alias_binary_with_its_textual_repr():
    raw = b"\x00\xff"
    assert typed_payload_digest(raw) == typed_payload_digest(memoryview(raw))
    assert typed_payload_digest(raw) == typed_payload_digest(bytearray(raw))
    assert typed_payload_digest(raw) != typed_payload_digest(str(raw))
    assert typed_payload_digest({"a": 1, "b": 2}) == typed_payload_digest({"b": 2, "a": 1})
    assert typed_payload_digest([1, 2]) != typed_payload_digest([2, 1])


def test_typed_digest_rejects_lossy_and_nondeterministic_custom_codecs():
    class Opaque:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return "same despite different contents"

    for value in (Opaque("A"), Opaque("B"), object(), object(), {1, 2}):
        with pytest.raises(TypeError, match="^UNSUPPORTED_RECEIPT_PAYLOAD_TYPE$"):
            typed_payload_digest({"rows": [{"value": value}]})


def test_typed_digest_rejects_polymorphic_scalar_and_container_codecs():
    # Previously `isinstance(int)` followed by `str(item)` silently aliased
    # distinct extension values whenever their subclasses hid the payload.
    class OpaqueInt(int):
        def __str__(self):
            return "opaque"

    class OpaqueStr(str):
        def encode(self, *_args, **_kwargs):
            return b"opaque"

    class OpaqueDecimal(Decimal):
        def __str__(self):
            return "opaque"

    class OpaqueMap(dict):
        def __getitem__(self, _key):
            return "opaque"

    class OpaqueList(list):
        def __iter__(self):
            return iter(("opaque",))

    values = (
        OpaqueInt(1),
        OpaqueInt(2),
        OpaqueStr("private-a"),
        OpaqueStr("private-b"),
        OpaqueDecimal("1.0"),
        OpaqueDecimal("2.0"),
        OpaqueMap({"key": "private-a"}),
        OpaqueList(["private-a"]),
    )
    for value in values:
        with pytest.raises(TypeError, match="^UNSUPPORTED_RECEIPT_PAYLOAD_TYPE$"):
            typed_payload_digest({"rows": [{"value": value}]})


def test_typed_digest_canonical_known_postgresql_scalars():
    values = [
        date(2026, 10, 25),
        datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
        time(12, 30, 0, 123456),
        timedelta(days=-2, seconds=1, microseconds=987654),
        Decimal("12.30"),
        UUID("4d9041e7-ec57-4ba5-91c2-fdc1a66279f0"),
        ip_address("192.0.2.15"),
        ip_interface("2001:db8::9/64"),
        ip_network("198.51.100.0/24"),
        Range(2, 9, bounds="[)"),
        Multirange([Range(2, 9), Range(11, 13)]),
    ]
    assert typed_payload_digest(values) == typed_payload_digest(list(values))
    for index in range(len(values)):
        changed = list(values)
        changed[index] = None
        assert typed_payload_digest(values) != typed_payload_digest(changed)


def test_query_fails_closed_before_receipt_for_unknown_result_type(monkeypatch):
    settings = Settings(database_url="postgresql://offline/offline", api_token="test-token")
    monkeypatch.setattr(db, "_runtime_identity", lambda conn: {"identity_digest": "a" * 64})
    monkeypatch.setattr(db, "connect", lambda settings: _Connection([{"value": object()}]))
    with pytest.raises(TypeError, match="^UNSUPPORTED_RECEIPT_PAYLOAD_TYPE$"):
        db.query_readonly(settings, "SELECT %s AS value", [1])
