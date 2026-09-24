import json
import os
import subprocess
import sys


def test_conformance_snapshot_generator(tmp_path) -> None:
    output = tmp_path / "snapshot.json"
    env = {**os.environ, "GITHUB_SHA": "test-commit"}

    subprocess.run(
        [
            sys.executable,
            "scripts/generate_conformance_snapshot.py",
            str(output),
        ],
        check=True,
        env=env,
    )

    snapshot = json.loads(output.read_text(encoding="utf-8"))

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
