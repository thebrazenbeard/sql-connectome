from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sql_connectome.config import get_settings
from sql_connectome.differential import run_differential_conformance


def main() -> None:
    output_path = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "artifacts/differential-conformance.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    settings = None
    if os.getenv("SQL_CONNECTOME_DATABASE_URL") and os.getenv(
        "SQL_CONNECTOME_API_TOKEN"
    ):
        get_settings.cache_clear()
        settings = get_settings()

    payload = run_differential_conformance(
        settings=settings,
        source_commit=os.getenv("GITHUB_SHA"),
    )
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(output_path)


if __name__ == "__main__":
    main()
