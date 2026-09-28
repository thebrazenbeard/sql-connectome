from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

import duckdb

from .conformance import ConformanceCase, ExecutionObservation, conformance_case_digest
from .engine_validation import EngineRuntimeIdentity, NativeEngineError
from .receipts import canonical_digest


class ConformanceRunner(Protocol):
    @property
    def runtime(self) -> EngineRuntimeIdentity: ...

    def execute(self, case: ConformanceCase, sql: str) -> ExecutionObservation: ...


@dataclass(frozen=True, slots=True)
class SQLiteRunner:
    runtime: EngineRuntimeIdentity = EngineRuntimeIdentity(
        "sqlite", "sqlite-conformance-v1", sqlite3.sqlite_version
    )

    def execute(self, case: ConformanceCase, sql: str) -> ExecutionObservation:
        connection = sqlite3.connect(":memory:")
        try:
            for statement in case.setup_sql:
                connection.execute(statement)
            try:
                cursor = connection.execute(sql)
                rows = tuple(tuple(row) for row in cursor.fetchall())
                error = None
            except Exception as exc:
                rows = None
                error = NativeEngineError(type(exc).__name__, str(exc))
            return ExecutionObservation(
                runtime=self.runtime,
                case_digest=conformance_case_digest(case),
                sql_digest=canonical_digest({"sql": sql}),
                rows=rows,
                native_error=error,
                session_facts=(("catalog", "main"), ("isolation", "in-memory")),
            )
        finally:
            connection.close()


@dataclass(frozen=True, slots=True)
class DuckDBRunner:
    runtime: EngineRuntimeIdentity = EngineRuntimeIdentity(
        "duckdb", "duckdb-conformance-v1", duckdb.__version__
    )

    def execute(self, case: ConformanceCase, sql: str) -> ExecutionObservation:
        connection = duckdb.connect(":memory:")
        try:
            for statement in case.setup_sql:
                connection.execute(statement)
            try:
                rows = tuple(tuple(row) for row in connection.execute(sql).fetchall())
                error = None
            except Exception as exc:
                rows = None
                error = NativeEngineError(type(exc).__name__, str(exc))
            return ExecutionObservation(
                runtime=self.runtime,
                case_digest=conformance_case_digest(case),
                sql_digest=canonical_digest({"sql": sql}),
                rows=rows,
                native_error=error,
                session_facts=(("catalog", "memory"), ("isolation", "in-memory")),
            )
        finally:
            connection.close()
