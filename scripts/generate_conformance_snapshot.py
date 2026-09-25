from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import sqlglot

from sql_connectome.connectome import (
    DEFAULT_CATALOG,
    dialect_semantic_profile,
    dialect_type_graph,
    list_dialects,
)
from sql_connectome.receipts import canonical_digest


def _rewrite_rows() -> list[dict[str, object]]:
    return [
        {
            "name": rule.name,
            "source_capability": rule.source_capability,
            "target_capabilities": sorted(rule.target_capabilities),
            "target_dialects": sorted(rule.target_dialects),
            "fidelity": rule.fidelity.value,
            "description": rule.description,
        }
        for rule in DEFAULT_CATALOG.rewrite_rules
    ]


def build_snapshot() -> dict[str, object]:
    dialect_inventory = list_dialects(dialects=DEFAULT_CATALOG.dialects)
    dialects: list[dict[str, object]] = []

    for dialect in dialect_inventory:
        dialect_id = str(dialect["dialect_id"])
        parser_dialect = DEFAULT_CATALOG.parser_adapters.get(dialect_id)

        semantic_profile: dict[str, object] | None = None
        type_graph_summary: dict[str, object] | None = None
        if parser_dialect:
            semantic_profile = dialect_semantic_profile(dialect_id, parser_dialect)
            type_graph = dialect_type_graph(
                dialect_id=dialect_id,
                parser_dialect=parser_dialect,
            )
            type_graph_summary = {
                "dialect_type_count": len(type_graph["dialect_types"]),
                "implicit_coercion_count": len(type_graph["implicit_coercions"]),
                "type_graph_digest": canonical_digest(type_graph),
            }

        dialects.append(
            {
                **dialect,
                "parser_dialect": parser_dialect,
                "semantic_profile": semantic_profile,
                "type_graph_summary": type_graph_summary,
            }
        )

    rewrites = _rewrite_rows()
    payload: dict[str, object] = {
        "schema": "SQL_CONNECTOME_CONFORMANCE_SNAPSHOT_V1",
        "source_commit": os.getenv("GITHUB_SHA"),
        "sqlglot_version": sqlglot.__version__,
        "dialect_count": len(DEFAULT_CATALOG.dialects),
        "parser_adapter_count": len(DEFAULT_CATALOG.parser_adapters),
        "catalog": {
            "admission": "SOURCE_CONTROLLED_DEFAULT",
            "automatic_plugin_discovery": False,
            "digest": DEFAULT_CATALOG.digest,
        },
        "dialects": dialects,
        "rewrite_rules": rewrites,
    }
    payload["snapshot_digest"] = canonical_digest(payload)
    return payload


def main() -> None:
    output_path = Path(
        sys.argv[1] if len(sys.argv) > 1 else "artifacts/conformance-snapshot.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_snapshot(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output_path)


if __name__ == "__main__":
    main()
