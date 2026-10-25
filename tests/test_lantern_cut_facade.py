"""Source-level fail-closed tests for the BT2 PostgreSQL V4 Lantern cut facade.

These tests use a fake connection and do not establish a qualified live Lantern runtime.
"""

from contextlib import nullcontext

import pytest

from sql_connectome import db
from sql_connectome.config import Settings


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _FakeConnection:
    def __init__(self, facade_id, *, payload_row=None):
        self.payload_row = payload_row
        self.cut = {
            "facade_id": facade_id,
            "profile_digest": "profile",
            "predecessor_digest": "predecessor",
            "policy_digest": "policy",
            "material_count": int(payload_row is not None),
            "exact_members": (
                [[payload_row[key] for key in (
                    "material_id", "canonical_digest", "semantic_key", "source_digest"
                )]]
                if payload_row is not None else []
            ),
        }
        self.payload_queries = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def transaction(self):
        return nullcontext()

    def execute(self, query, params=None):
        if "FROM bt2.material_cut_v1" in query:
            return _Rows([self.cut])
        if "FROM bt2.runtime_visible_materials_v1" in query:
            self.payload_queries += 1
            assert "public.digest(" in query
            assert "convert_to(canonical_payload::text, 'UTF8'), 'sha256'" in query
            return _Rows([self.payload_row] if self.payload_row is not None else [])
        return _Rows([])


def _call_cut(monkeypatch, facade_id, *, payload_row=None):
    conn = _FakeConnection(facade_id, payload_row=payload_row)
    monkeypatch.setattr(db, "connect", lambda settings: conn)
    monkeypatch.setattr(
        db,
        "_runtime_identity",
        lambda conn: {"identity_digest": "test-runtime"},
    )
    settings = Settings(
        database_url="postgresql://postgres:postgres@localhost:5432/test",
        api_token="unit-test-token",
    )
    return conn, settings


@pytest.mark.parametrize(
    "facade_id",
    [
        "LANTERN_MATERIAL_CUT_V1",
        "BT2_MATERIAL_CUT_V0",
        "bt2_material_cut_v1",
        "BT2_MATERIAL_CUT_V1 ",
        "",
        None,
    ],
)
def test_lantern_current_cut_rejects_wrong_facade_before_payload(monkeypatch, facade_id):
    conn, settings = _call_cut(monkeypatch, facade_id)

    with pytest.raises(ValueError, match="LANTERN_CUT_FACADE_MISMATCH"):
        db.lantern_current_cut(settings)

    assert conn.payload_queries == 0


def test_lantern_current_cut_accepts_canonical_facade_with_bound_empty_cut(monkeypatch):
    conn, settings = _call_cut(monkeypatch, "BT2_MATERIAL_CUT_V1")

    result = db.lantern_current_cut(settings)

    assert result["cut"]["facade_id"] == "BT2_MATERIAL_CUT_V1"
    assert result["payload"] == []
    assert conn.payload_queries == 1


def _material_row(*, verified_digest: str) -> dict:
    return {
        "material_id": "material-1",
        "project_scope": "PROJECT_LANTERN",
        "schema_version": 1,
        "semantic_key": "key",
        "canonical_digest": "stored-canonical-digest",
        "source_digest": "source",
        "canonical_payload": {"semantic_role": "inert", "subject_key": "fake"},
        "verified_canonical_digest": verified_digest,
        "created_at": "2026-10-25",
        "receipt_id": "receipt-1",
        "profile_digest": "profile",
        "policy_digest": "policy",
    }


def test_lantern_current_cut_rejects_payload_changed_without_digest(monkeypatch):
    row = _material_row(verified_digest="different-recomputed-digest")
    _, settings = _call_cut(monkeypatch, "BT2_MATERIAL_CUT_V1", payload_row=row)

    with pytest.raises(ValueError, match="LANTERN_CANONICAL_PAYLOAD_DIGEST_MISMATCH"):
        db.lantern_current_cut(settings)


def test_lantern_current_cut_excludes_internal_digest_check_from_receipt_payload(monkeypatch):
    row = _material_row(verified_digest="stored-canonical-digest")
    _, settings = _call_cut(monkeypatch, "BT2_MATERIAL_CUT_V1", payload_row=row)

    result = db.lantern_current_cut(settings)
    assert result["payload"] == [
        {key: value for key, value in row.items() if key != "verified_canonical_digest"}
    ]
    assert result["receipt"]["kind"] == "LANTERN_CURRENT_CUT"
