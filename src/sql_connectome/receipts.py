from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def make_receipt(kind: str, subject: dict[str, Any], *, issued_at: str | None = None) -> dict[str, Any]:
    timestamp = issued_at or datetime.now(UTC).isoformat()
    body = {
        "schema": "SQL_CONNECTOME_RECEIPT_V1",
        "kind": kind,
        "issued_at": timestamp,
        "subject": subject,
    }
    return {**body, "receipt_digest": canonical_digest(body)}
