from __future__ import annotations

from typing import Any

from .config import Settings
from .connectome import transpile_sql_text
from .db import validate_postgresql_readonly
from .receipts import canonical_digest, make_receipt


def qualify_translation_to_postgresql(
    settings: Settings,
    sql: str,
    source_dialect: str,
    *,
    allow_lossy: bool = False,
) -> dict[str, Any]:
    translation = transpile_sql_text(
        sql,
        source_dialect,
        "postgresql",
        allow_lossy=allow_lossy,
    )
    target_sql = str(translation["target_sql"])
    engine = validate_postgresql_readonly(settings, target_sql)

    engine_status = str(engine["validation"]["status"])
    status = "PASS" if engine_status == "PASS" else "FAIL"
    plan = translation["plan"]
    target_runtime = engine["runtime"]

    subject = {
        "source_dialect": source_dialect,
        "target_dialect": "postgresql",
        "source_sql_digest": canonical_digest(sql.strip()),
        "target_sql_digest": canonical_digest(target_sql),
        "translation_fidelity": plan["fidelity"],
        "translation_fidelity_scope": plan["fidelity_scope"],
        "target_runtime_identity_digest": target_runtime["identity_digest"],
        "engine_validation_status": engine_status,
    }

    return {
        "schema": "SQL_CONNECTOME_TRANSLATION_QUALIFICATION_V1",
        "qualification": {
            "status": status,
            "source_dialect": source_dialect,
            "target_dialect": "postgresql",
            "translation_fidelity": plan["fidelity"],
            "translation_fidelity_scope": plan["fidelity_scope"],
            "behavioral_equivalence": "NOT_ESTABLISHED",
            "query_executed": False,
            "authority": "VALIDATION_ONLY",
        },
        "translation": translation,
        "engine_validation": engine,
        "receipt": make_receipt("TRANSLATION_QUALIFICATION", subject),
    }
