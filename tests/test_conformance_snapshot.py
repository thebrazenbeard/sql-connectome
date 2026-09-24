from scripts.generate_conformance_snapshot import build_snapshot


def test_conformance_snapshot_covers_dialects_and_rewrites(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", "test-commit")

    snapshot = build_snapshot()

    assert snapshot["schema"] == "SQL_CONNECTOME_CONFORMANCE_SNAPSHOT_V1"
    assert snapshot["source_commit"] == "test-commit"
    assert snapshot["dialect_count"] >= 28
    assert snapshot["parser_adapter_count"] >= 28
    assert len(snapshot["snapshot_digest"]) == 64

    dialect_ids = {row["dialect_id"] for row in snapshot["dialects"]}
    assert {"postgresql", "mysql", "bigquery", "snowflake", "duckdb"}.issubset(
        dialect_ids
    )

    rewrite_names = {row["name"] for row in snapshot["rewrite_rules"]}
    assert "qualify-via-derived-table" in rewrite_names
