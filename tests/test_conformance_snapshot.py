import json
import os
import subprocess
import sys

from sql_connectome.connectome import DEFAULT_CATALOG


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
    assert snapshot["catalog"]["admission"] == "SOURCE_CONTROLLED_DEFAULT"
    assert snapshot["catalog"]["automatic_plugin_discovery"] is False
    assert snapshot["catalog"]["digest"] == DEFAULT_CATALOG.digest
    assert len(snapshot["snapshot_digest"]) == 64
    assert len(snapshot["operation_catalog_digest"]) == 64
    assert snapshot["operation_catalog"]["schema"] == "SQL_CONNECTOME_OPERATION_CATALOG_V1"
    assert snapshot["operation_catalog"]["operation_count"] >= 30
    operation_ids = {
        row["semantic_id"] for row in snapshot["operation_catalog"]["operations"]
    }
    assert {"arithmetic.divide", "aggregate.count", "string.concat"}.issubset(
        operation_ids
    )

    dialect_ids = {row["dialect_id"] for row in snapshot["dialects"]}
    assert {"postgresql", "mysql", "bigquery", "snowflake", "duckdb"}.issubset(
        dialect_ids
    )

    by_id = {row["dialect_id"]: row for row in snapshot["dialects"]}
    postgres_type_graph = by_id["postgresql"]["type_graph_summary"]
    assert postgres_type_graph is not None
    assert postgres_type_graph["dialect_type_count"] >= 0
    assert postgres_type_graph["implicit_coercion_count"] >= 0
    assert len(postgres_type_graph["type_graph_digest"]) == 64

    rewrite_names = {row["name"] for row in snapshot["rewrite_rules"]}
    assert "qualify-via-derived-table" in rewrite_names
