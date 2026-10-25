"""Gateway V1 client route: isolated fake-connection contract tests only.

Real PostgreSQL owner/ACL, transport, and deployed consumer gates remain separate.
"""

import hashlib
from contextlib import nullcontext
from copy import deepcopy

import pytest
from pydantic import ValidationError

from sql_connectome import db
from sql_connectome.config import Settings

PG_PAYLOAD = '{"semantic_role": "inert", "subject_key": "test"}'
DIGEST = hashlib.sha256(PG_PAYLOAD.encode("utf-8")).hexdigest()
MATERIAL = {
    "material_id": "00000000-0000-0000-0000-000000000001",
    "project_scope": "PROJECT_LANTERN",
    "schema_version": "v1",
    "semantic_key": "semantic-1",
    "canonical_digest": DIGEST,
    "source_digest": "source-1",
    "canonical_payload": {"semantic_role": "inert", "subject_key": "test"},
    "canonical_payload_pg_text": PG_PAYLOAD,
    "created_at": "2026-10-25T00:00:00Z",
    "receipt_id": "00000000-0000-0000-0000-000000000002",
    "profile_digest": "profile-current",
    "policy_digest": "policy-current",
}
CUT = {
    "facade_id": "BT2_MATERIAL_CUT_V1",
    "profile_digest": "profile-current",
    "predecessor_digest": "profile-old",
    "policy_digest": "policy-current",
    "material_count": 1,
    "exact_members": [[
        MATERIAL["material_id"],
        MATERIAL["canonical_digest"],
        MATERIAL["semantic_key"],
        MATERIAL["source_digest"],
    ]],
}


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _GatewayConnection:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def transaction(self):
        return nullcontext()

    def execute(self, query, params=None):
        self.queries.append((query, params))
        if "lantern_read.current_cut_v1()" in query:
            return _Rows([{"snapshot": deepcopy(self.snapshot)}])
        if "bt2." in query or "SET ROLE" in query:
            raise AssertionError("Gateway client attempted a privileged fallback")
        return _Rows([])


def _run(monkeypatch, snapshot, *, scope="PROJECT_LANTERN"):
    conn = _GatewayConnection(snapshot)
    monkeypatch.setattr(db, "connect", lambda _settings: conn)
    monkeypatch.setattr(db, "_runtime_identity", lambda _conn: {"identity_digest": "db-id"})
    settings = Settings(
        database_url="postgresql://example.invalid/test",
        api_token="test-token",
        lantern_route="gateway_v1",
    )
    return conn, lambda: db.lantern_current_cut(settings, scope)


def _snapshot():
    return {
        "schema": "BT2_LANTERN_READ_GATEWAY_V1",
        "project_scope": "PROJECT_LANTERN",
        "cut": deepcopy(CUT),
        "payload": [deepcopy(MATERIAL)],
    }


def test_gateway_is_opt_in_and_invalid_route_fails_closed():
    settings = Settings(database_url="postgresql://example.invalid/test", api_token="token")
    assert settings.lantern_route == "legacy_v4"
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://example.invalid/test",
            api_token="token",
            lantern_route="owner_fallback",
        )


def test_gateway_uses_only_versioned_api_and_binds_receipt(monkeypatch):
    conn, call = _run(monkeypatch, _snapshot())
    result = call()
    assert result["cut"] == CUT
    assert result["payload"] == [
        {k: v for k, v in MATERIAL.items() if k != "canonical_payload_pg_text"}
    ]
    assert result["receipt"]["subject"]["route"] == "gateway_v1"
    assert result["receipt"]["subject"]["gateway_schema"] == "BT2_LANTERN_READ_GATEWAY_V1"
    assert sum("lantern_read.current_cut_v1()" in q for q, _ in conn.queries) == 1
    assert all("bt2." not in q for q, _ in conn.queries)


def test_gateway_rejects_other_scope_without_opening_connection(monkeypatch):
    _conn, call = _run(monkeypatch, _snapshot(), scope="ANOTHER_PROJECT")
    with pytest.raises(ValueError, match="LANTERN_GATEWAY_SCOPE_NOT_ADMITTED"):
        call()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema", "BT2_LANTERN_READ_GATEWAY_V0", "LANTERN_GATEWAY_SHAPE_INVALID"),
        ("project_scope", "ANOTHER_PROJECT", "LANTERN_GATEWAY_SHAPE_INVALID"),
        ("payload", "bad", "LANTERN_GATEWAY_SHAPE_INVALID"),
    ],
)
def test_gateway_rejects_malformed_envelope(monkeypatch, field, value, message):
    snapshot = _snapshot()
    snapshot[field] = value
    _, call = _run(monkeypatch, snapshot)
    with pytest.raises(ValueError, match=message):
        call()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("canonical_payload_pg_text", '{"semantic_role":"changed"}', "PAYLOAD_MISMATCH"),
        ("canonical_payload_pg_text", "not-json", "PAYLOAD_INVALID"),
        ("canonical_digest", "forged", "PAYLOAD_MEMBERSHIP_MISMATCH"),
        ("profile_digest", "prior-profile", "PAYLOAD_BINDING_MISMATCH"),
        ("policy_digest", "other-policy", "PAYLOAD_BINDING_MISMATCH"),
        ("project_scope", "ANOTHER_PROJECT", "PAYLOAD_BINDING_MISMATCH"),
        ("semantic_key", "different", "PAYLOAD_MEMBERSHIP_MISMATCH"),
    ],
)
def test_gateway_rejects_corrupt_payload(monkeypatch, field, value, message):
    snapshot = _snapshot()
    snapshot["payload"][0][field] = value
    _, call = _run(monkeypatch, snapshot)
    with pytest.raises(ValueError, match=message):
        call()


def test_gateway_rejects_empty_cut_and_wrong_member_count(monkeypatch):
    snapshot = _snapshot()
    snapshot["cut"]["material_count"] = 0
    _, call = _run(monkeypatch, snapshot)
    with pytest.raises(ValueError, match="LANTERN_GATEWAY_EMPTY_CUT"):
        call()

    snapshot = _snapshot()
    snapshot["cut"]["material_count"] = 2
    _, call = _run(monkeypatch, snapshot)
    with pytest.raises(ValueError, match="LANTERN_PAYLOAD_COUNT_MISMATCH"):
        call()


def test_gateway_rejects_matching_forged_member_digest(monkeypatch):
    snapshot = _snapshot()
    snapshot["payload"][0]["canonical_digest"] = "forged"
    snapshot["cut"]["exact_members"][0][1] = "forged"
    _, call = _run(monkeypatch, snapshot)
    with pytest.raises(ValueError, match="LANTERN_CANONICAL_PAYLOAD_DIGEST_MISMATCH"):
        call()


def test_gateway_rejects_forged_numeric_count(monkeypatch):
    snapshot = _snapshot()
    snapshot["cut"]["material_count"] = "1"
    _, call = _run(monkeypatch, snapshot)
    with pytest.raises(ValueError, match="LANTERN_GATEWAY_SHAPE_INVALID"):
        call()


@pytest.mark.parametrize(
    ("pg_text", "claimed_payload", "expected"),
    [
        ('{"value": 1}', {"value": True}, "LANTERN_GATEWAY_PAYLOAD_MISMATCH"),
        ('{"value": 0}', {"value": False}, "LANTERN_GATEWAY_PAYLOAD_MISMATCH"),
        (
            '{"values": [{"value": 1}]}',
            {"values": [{"value": True}]},
            "LANTERN_GATEWAY_PAYLOAD_MISMATCH",
        ),
        (
            '{"value": 2, "value": 1}',
            {"value": 1},
            "LANTERN_GATEWAY_PAYLOAD_INVALID",
        ),
        (
            '{"value": NaN}',
            {"value": None},
            "LANTERN_GATEWAY_PAYLOAD_INVALID",
        ),
    ],
)
def test_gateway_requires_type_strict_and_unambiguous_json(
    monkeypatch, pg_text, claimed_payload, expected,
):
    # Bind the claimed digest and exact cut members to the attacker's raw
    # text. Even with those values in agreement the canonical payload must
    # not silently acquire a different JSON type or duplicate-key meaning.
    snapshot = _snapshot()
    digest = hashlib.sha256(pg_text.encode("utf-8")).hexdigest()
    snapshot["payload"][0].update({
        "canonical_payload_pg_text": pg_text,
        "canonical_payload": claimed_payload,
        "canonical_digest": digest,
    })
    snapshot["cut"]["exact_members"][0][1] = digest
    _, call = _run(monkeypatch, snapshot)
    with pytest.raises(ValueError, match=expected):
        call()
