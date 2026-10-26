from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from typing import Any
from uuid import UUID

from psycopg.types.multirange import Multirange
from psycopg.types.range import Range

TYPED_PAYLOAD_DIGEST_FORMAT = "SQL_CONNECTOME_TYPED_PAYLOAD_V1_SHA256"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def typed_payload_digest(value: Any) -> str:
    """Stream a type-aware digest without copying the full result into JSON.

    The existing canonical JSON digest intentionally preserves legacy receipt
    identities. This digest is for read-query parameter/result payloads, where
    PostgreSQL byte strings must not collide with their textual representation.
    """
    digest = hashlib.sha256()
    digest.update(TYPED_PAYLOAD_DIGEST_FORMAT.encode("ascii") + b"\x00")

    def scalar(tag: bytes, raw: bytes | memoryview) -> None:
        digest.update(tag)
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b":")
        digest.update(raw)

    def visit(item: Any) -> None:
        # Only exact built-in/known PostgreSQL codec types may supply the
        # canonical bytes. Subclasses can override str(), repr(), encode(),
        # iteration or mapping access and silently alias different values.
        kind = type(item)
        if item is None:
            digest.update(b"n")
        elif kind is bool:
            digest.update(b"t" if item else b"f")
        elif kind is int:
            scalar(b"i", str(item).encode("ascii"))
        elif kind is float:
            scalar(b"r", repr(item).encode("ascii"))
        elif kind is str:
            scalar(b"s", item.encode("utf-8"))
        elif kind in (bytes, bytearray, memoryview):
            scalar(b"b", memoryview(item))
        elif kind is Decimal:
            scalar(b"d", str(item).encode("ascii"))
        elif kind is UUID:
            scalar(b"u", item.bytes)
        elif kind is datetime:
            scalar(b"z", item.isoformat(timespec="microseconds").encode("utf-8"))
        elif kind is date:
            scalar(b"D", item.isoformat().encode("ascii"))
        elif kind is time:
            scalar(b"T", item.isoformat(timespec="microseconds").encode("utf-8"))
        elif kind is timedelta:
            scalar(b"L", f"{item.days}:{item.seconds}:{item.microseconds}".encode("ascii"))
        elif kind in (
            IPv4Address,
            IPv4Interface,
            IPv4Network,
            IPv6Address,
            IPv6Interface,
            IPv6Network,
        ):
            scalar(b"p", kind.__name__.encode("ascii"))
            scalar(b"v", str(item).encode("ascii"))
        elif kind is Range:
            digest.update(b"R")
            visit(item.isempty)
            if not item.isempty:
                visit(item.bounds)
                visit(item.lower)
                visit(item.upper)
            digest.update(b"r")
        elif kind is Multirange:
            digest.update(b"M")
            for member in item:
                visit(member)
            digest.update(b"m")
        elif kind is dict:
            digest.update(b"{")
            if not all(type(key) is str for key in item):
                raise TypeError("Receipt payload mapping keys must be strings")
            for key in sorted(item):
                visit(key)
                visit(item[key])
            digest.update(b"}")
        elif kind in (list, tuple):
            digest.update(b"[" if kind is list else b"(")
            for member in item:
                visit(member)
            digest.update(b"]" if kind is list else b")")
        else:
            # Unknown PostgreSQL codecs are not attestable with str(): it can
            # discard distinct internal values or include process addresses.
            raise TypeError("UNSUPPORTED_RECEIPT_PAYLOAD_TYPE")

    visit(value)
    return digest.hexdigest()


def make_receipt(
    kind: str,
    subject: dict[str, Any],
    *,
    issued_at: str | None = None,
) -> dict[str, Any]:
    timestamp = issued_at or datetime.now(UTC).isoformat()
    body = {
        "schema": "SQL_CONNECTOME_RECEIPT_V1",
        "kind": kind,
        "issued_at": timestamp,
        "subject": subject,
    }
    return {**body, "receipt_digest": canonical_digest(body)}
