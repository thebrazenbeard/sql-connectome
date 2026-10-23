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
    def __init__(self, facade_id):
        self.cut = {
            "facade_id": facade_id,
            "profile_digest": "profile",
            "predecessor_digest": "predecessor",
            "policy_digest": "policy",
            "material_count": 0,
            "exact_members": [],
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
            return _Rows([])
        return _Rows([])


def _call_cut(monkeypatch, facade_id):
    conn = _FakeConnection(facade_id)
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
