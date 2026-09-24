from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import sqlglot

from sql_connectome.connectome import (
    DEFAULT_DIALECTS,
    DEFAULT_REWRITE_RULES,
    dialect_semantic_profile,
    list_dialects,
)
from sql_connectome.connectome.text_pipeline import SQLGLOT_DIALECTS
from sql_connectome.receipts import canonical_digest


def build_snapshot() -> dict[str, object]:
    dialects: list[dict[str, object]] = []

    for dialect in list_dialects():
        dialect_id = str(dialect["dialect_id"])
        parser_dialect = SQLGLOT_DIALECTS.get(dialect_id)

        semantic_profile: dict[str, object] | None = None
        if parser_dialect:
            semantic_profile = dialect_semantic_profile(dialect_id, parser_dialect)

        dialects.append(
            {
                **dialect,
                "parser_dialect": parser_dialect,
                "semantic_profile": semantic_profile,
            }
        )

    rewrites = [
        {
            "name": rule.name,
            "source_capability": rule.source_capability,
            "target_capabilities": sorted(rule.target_capabilities),
            "target_dialects": sorted(rule.target_dialects),
            "fidelity": rule.fidelity.value,
            "description": rule.description,
        }
        for rule in DEFAULT_REWRITE_RULES
    ]

    payload: dict[str, object] = {
        "schema": "SQL_CONNECTOME_CONFORMANCE_SNAPSHOT_V1",
        "source_commit": os.getenv("GITHUB_SHA"),
        "sqlglot_version": sqlglot.__version__,
        "dialect_count": len(DEFAULT_DIALECTS),
        "parser_adapter_count": len(SQLGLOT_DIALECTS),
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
