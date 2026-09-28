from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .receipts import canonical_digest


class ValidationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class EngineRuntimeIdentity:
    engine: str
    adapter_id: str
    version: str | None = None
    facts: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "adapter_id": self.adapter_id,
            "version": self.version,
            "facts": dict(sorted(self.facts)),
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


@dataclass(frozen=True, slots=True)
class NativeEngineError:
    error_class: str
    message: str
    native_fields: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_class": self.error_class,
            "message": self.message,
            "native_fields": dict(sorted(self.native_fields)),
        }


@dataclass(frozen=True, slots=True)
class EngineValidationResult:
    runtime: EngineRuntimeIdentity
    sql_digest: str
    schema_context_digest: str
    status: ValidationStatus
    validation_mode: str
    native_payload: Any = None
    native_error: NativeEngineError | None = None
    query_executed: bool = False
    evidence_ceiling: str = "ENGINE_VALIDATION"
    behavioral_equivalence: str = "NOT_ESTABLISHED"
    receipt: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_ENGINE_VALIDATION_V1",
            "runtime": self.runtime.as_dict(),
            "sql_digest": self.sql_digest,
            "schema_context_digest": self.schema_context_digest,
            "status": self.status.value,
            "validation_mode": self.validation_mode,
            "query_executed": self.query_executed,
            "evidence_ceiling": self.evidence_ceiling,
            "behavioral_equivalence": self.behavioral_equivalence,
            "native_payload": self.native_payload,
            "error": self.native_error.as_dict() if self.native_error else None,
            "receipt": self.receipt,
        }


def build_engine_validation_result(
    *,
    runtime: EngineRuntimeIdentity,
    sql: str,
    schema_context: Any,
    status: ValidationStatus,
    validation_mode: str,
    native_payload: Any = None,
    native_error: NativeEngineError | None = None,
) -> EngineValidationResult:
    sql_digest = canonical_digest({"sql": sql})
    schema_context_digest = canonical_digest(schema_context)
    receipt_payload = {
        "kind": "ENGINE_VALIDATION_V1",
        "runtime_digest": runtime.digest(),
        "sql_digest": sql_digest,
        "schema_context_digest": schema_context_digest,
        "status": status.value,
        "validation_mode": validation_mode,
        "query_executed": False,
        "evidence_ceiling": "ENGINE_VALIDATION",
        "native_error_digest": (
            canonical_digest(native_error.as_dict()) if native_error else None
        ),
    }
    return EngineValidationResult(
        runtime=runtime,
        sql_digest=sql_digest,
        schema_context_digest=schema_context_digest,
        status=status,
        validation_mode=validation_mode,
        native_payload=native_payload,
        native_error=native_error,
        receipt=canonical_digest(receipt_payload),
    )



def engine_validation_manifest() -> dict[str, Any]:
    adapters = {
        "mysql": {
            "adapter_id": "mysql-v1",
            "validation_mode": "EXPLAIN_FORMAT_JSON",
            "qualification": "PROTOCOL_TESTED",
            "behavioral_equivalence": "NOT_ESTABLISHED",
        },
        "mariadb": {
            "adapter_id": "mariadb-v1",
            "validation_mode": "EXPLAIN_FORMAT_JSON",
            "qualification": "PROTOCOL_TESTED",
            "behavioral_equivalence": "NOT_ESTABLISHED",
        },
        "trino": {
            "adapter_id": "trino-v1",
            "validation_mode": "EXPLAIN_TYPE_VALIDATE",
            "qualification": "PROTOCOL_TESTED",
            "behavioral_equivalence": "NOT_ESTABLISHED",
        },
    }
    payload = {
        "schema": "SQL_CONNECTOME_ENGINE_VALIDATION_MANIFEST_V1",
        "adapters": adapters,
    }
    return {**payload, "digest": canonical_digest(payload)}
