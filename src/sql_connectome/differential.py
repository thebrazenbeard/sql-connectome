from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import duckdb
import psycopg

from .config import Settings
from .db import platform_health, query_readonly
from .duckdb_engine import hardened_duckdb_session
from .receipts import canonical_digest, make_receipt
from .sql_guard import validate_readonly_sql
from .sqlite_engine import hardened_sqlite_session

MAX_PROBE_ROWS = 32
MAX_PROBES = 64


@dataclass(frozen=True, slots=True)
class DifferentialProbe:
    probe_id: str
    sql: str
    purpose: str
    tags: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "probe_id": self.probe_id,
            "sql": self.sql,
            "purpose": self.purpose,
            "tags": list(self.tags),
        }


DEFAULT_PROBES: tuple[DifferentialProbe, ...] = (
    DifferentialProbe(
        probe_id="literal_integer_addition",
        sql="SELECT 1 + 2 AS value",
        purpose="Portable integer arithmetic baseline.",
        tags=("arithmetic", "portable-baseline"),
    ),
    DifferentialProbe(
        probe_id="integer_division",
        sql="SELECT 5 / 2 AS value",
        purpose="Expose integer-division result and type differences.",
        tags=("arithmetic", "division", "known-divergence-candidate"),
    ),
    DifferentialProbe(
        probe_id="division_by_zero",
        sql="SELECT 1 / 0 AS value",
        purpose="Expose error, NULL, or non-finite division-by-zero behavior.",
        tags=("arithmetic", "division-by-zero", "known-divergence-candidate"),
    ),
    DifferentialProbe(
        probe_id="null_ordering_asc",
        sql=(
            "WITH t(x) AS (VALUES (1), (NULL), (2)) "
            "SELECT x FROM t ORDER BY x ASC"
        ),
        purpose="Expose default NULL ordering for ascending sort.",
        tags=("ordering", "nulls", "known-divergence-candidate"),
    ),
    DifferentialProbe(
        probe_id="concat_null_operator",
        sql="SELECT 'a' || NULL AS value",
        purpose="Compare NULL propagation through the concatenation operator.",
        tags=("string", "nulls"),
    ),
    DifferentialProbe(
        probe_id="null_predicate_three_valued_logic",
        sql="SELECT (NULL = NULL) AS value",
        purpose="Expose three-valued NULL comparison semantics.",
        tags=("nulls", "three-valued-logic"),
    ),
    DifferentialProbe(
        probe_id="coalesce_mixed_null_integer",
        sql="SELECT COALESCE(NULL, 7) AS value",
        purpose="Compare NULL elimination and resulting scalar type.",
        tags=("nulls", "coalesce", "types"),
    ),
    DifferentialProbe(
        probe_id="case_null_branch",
        sql="SELECT CASE WHEN NULL THEN 1 ELSE 2 END AS value",
        purpose="Compare UNKNOWN predicate handling in CASE.",
        tags=("nulls", "case", "three-valued-logic"),
    ),
    DifferentialProbe(
        probe_id="decimal_division",
        sql="SELECT CAST(5 AS DECIMAL(10,2)) / CAST(2 AS DECIMAL(10,2)) AS value",
        purpose="Expose decimal division value and result-type differences.",
        tags=("numeric", "decimal", "precision", "known-divergence-candidate"),
    ),
    DifferentialProbe(
        probe_id="negative_round_half",
        sql="SELECT ROUND(-2.5) AS value",
        purpose="Expose negative half rounding behavior.",
        tags=("numeric", "rounding", "known-divergence-candidate"),
    ),
    DifferentialProbe(
        probe_id="round_half",
        sql="SELECT ROUND(2.5) AS value",
        purpose="Compare scalar rounding of a positive half value.",
        tags=("numeric", "rounding"),
    ),
    DifferentialProbe(
        probe_id="explicit_nulls_first",
        sql="WITH t(x) AS (VALUES (1), (NULL), (2)) SELECT x FROM t ORDER BY x ASC NULLS FIRST",
        purpose="Test explicit NULL ordering rather than engine defaults.",
        tags=("ordering", "nulls", "explicit-semantics"),
    ),
    DifferentialProbe(
        probe_id="duplicate_preserving_union_all",
        sql="SELECT x FROM (SELECT 1 AS x UNION ALL SELECT 1 AS x) q ORDER BY x",
        purpose="Verify duplicate-preserving set operation semantics.",
        tags=("duplicates", "set-operation", "ordering"),
    ),
    DifferentialProbe(
        probe_id="distinct_duplicate_elimination",
        sql="SELECT DISTINCT x FROM (SELECT 1 AS x UNION ALL SELECT 1 AS x) q",
        purpose="Verify explicit duplicate elimination semantics.",
        tags=("duplicates", "distinct", "set-operation"),
    ),
    DifferentialProbe(
        probe_id="left_join_null_extension",
        sql=("WITH l(id) AS (VALUES (1), (2)), r(id) AS (VALUES (1)) "
             "SELECT l.id, r.id AS rid FROM l LEFT JOIN r ON l.id = r.id ORDER BY l.id"),
        purpose="Exercise outer-join cardinality and NULL extension.",
        tags=("join", "cardinality", "nulls"),
    ),
    DifferentialProbe(
        probe_id="join_duplicate_amplification",
        sql=("WITH l(id) AS (VALUES (1), (1)), r(id) AS (VALUES (1), (1)) "
             "SELECT COUNT(*) AS value FROM l JOIN r ON l.id = r.id"),
        purpose="Detect accidental suppression of many-to-many join amplification.",
        tags=("join", "cardinality", "duplicates"),
    ),
)


def _decimal_text(value: Decimal) -> str:
    if value.is_zero():
        return "0"
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _normalize_cell(value: Any) -> dict[str, object]:
    if value is None:
        return {"family": "NULL", "value": None, "comparison_value": None}

    if isinstance(value, bool):
        return {
            "family": "BOOLEAN",
            "value": value,
            "comparison_value": value,
        }

    if isinstance(value, int):
        text = str(value)
        return {
            "family": "INTEGER",
            "value": text,
            "comparison_value": {"numeric": text},
        }

    if isinstance(value, Decimal):
        text = _decimal_text(value)
        return {
            "family": "DECIMAL",
            "value": text,
            "comparison_value": {"numeric": text},
        }

    if isinstance(value, float):
        if math.isnan(value):
            text = "NaN"
        elif math.isinf(value):
            text = "Infinity" if value > 0 else "-Infinity"
        else:
            text = _decimal_text(Decimal(str(value)))
        return {
            "family": "FLOAT",
            "value": text,
            "comparison_value": {"numeric": text},
        }

    if isinstance(value, str):
        return {
            "family": "STRING",
            "value": value,
            "comparison_value": value,
        }

    if isinstance(value, (bytes, bytearray, memoryview)):
        text = bytes(value).hex()
        return {
            "family": "BINARY",
            "value": text,
            "comparison_value": text,
        }

    if isinstance(value, datetime):
        text = value.isoformat()
        return {
            "family": "TIMESTAMP",
            "value": text,
            "comparison_value": text,
        }

    if isinstance(value, date):
        text = value.isoformat()
        return {
            "family": "DATE",
            "value": text,
            "comparison_value": text,
        }

    if isinstance(value, time):
        text = value.isoformat()
        return {
            "family": "TIME",
            "value": text,
            "comparison_value": text,
        }

    text = str(value)
    return {
        "family": type(value).__name__.upper(),
        "value": text,
        "comparison_value": text,
    }


def _normalize_rows(
    columns: list[str],
    rows: Iterable[Iterable[Any]],
) -> dict[str, object]:
    normalized_rows: list[list[dict[str, object]]] = []
    for row in rows:
        normalized_rows.append([_normalize_cell(value) for value in row])

    value_projection = [
        [cell["comparison_value"] for cell in row]
        for row in normalized_rows
    ]
    type_projection = [
        [cell["family"] for cell in row]
        for row in normalized_rows
    ]

    return {
        "columns": columns,
        "rows": normalized_rows,
        "value_projection": value_projection,
        "type_projection": type_projection,
        "row_count": len(normalized_rows),
    }


def _engine_success(
    *,
    engine: str,
    runtime: dict[str, Any],
    columns: list[str],
    rows: Iterable[Iterable[Any]],
) -> dict[str, object]:
    normalized = _normalize_rows(columns, rows)
    return {
        "engine": engine,
        "status": "PASS",
        "runtime": runtime,
        **normalized,
    }


def _engine_error(
    *,
    engine: str,
    runtime: dict[str, Any] | None,
    exc: Exception,
) -> dict[str, object]:
    return {
        "engine": engine,
        "status": "ERROR",
        "runtime": runtime,
        "error": {
            "error_class": exc.__class__.__name__,
            "message": str(exc).splitlines()[0],
        },
    }


def _run_duckdb_probe(probe: DifferentialProbe) -> dict[str, object]:
    statement = validate_readonly_sql(probe.sql)
    with hardened_duckdb_session() as (conn, identity):
        try:
            cursor = conn.execute(statement)
            rows = cursor.fetchmany(MAX_PROBE_ROWS + 1)
            if len(rows) > MAX_PROBE_ROWS:
                raise ValueError("DIFFERENTIAL_PROBE_ROW_LIMIT_EXCEEDED")
            columns = [str(column[0]) for column in (cursor.description or ())]
            return _engine_success(
                engine="duckdb",
                runtime=identity,
                columns=columns,
                rows=rows,
            )
        except duckdb.Error as exc:
            return _engine_error(engine="duckdb", runtime=identity, exc=exc)


def _run_sqlite_probe(probe: DifferentialProbe) -> dict[str, object]:
    statement = validate_readonly_sql(probe.sql)
    with hardened_sqlite_session() as (conn, identity):
        try:
            cursor = conn.execute(statement)
            rows = cursor.fetchmany(MAX_PROBE_ROWS + 1)
            if len(rows) > MAX_PROBE_ROWS:
                raise ValueError("DIFFERENTIAL_PROBE_ROW_LIMIT_EXCEEDED")
            columns = [str(column[0]) for column in (cursor.description or ())]
            return _engine_success(
                engine="sqlite",
                runtime=identity,
                columns=columns,
                rows=rows,
            )
        except sqlite3.Error as exc:
            return _engine_error(engine="sqlite", runtime=identity, exc=exc)


def _run_postgresql_probe(
    probe: DifferentialProbe,
    settings: Settings,
    runtime: dict[str, Any],
) -> dict[str, object]:
    try:
        result = query_readonly(settings, probe.sql)
    except psycopg.Error as exc:
        return _engine_error(engine="postgresql", runtime=runtime, exc=exc)

    if result["truncated"] or len(result["rows"]) > MAX_PROBE_ROWS:
        raise ValueError("DIFFERENTIAL_PROBE_ROW_LIMIT_EXCEEDED")

    columns = [str(column) for column in result["columns"]]
    rows = [
        [row[column] for column in columns]
        for row in result["rows"]
    ]
    return _engine_success(
        engine="postgresql",
        runtime=result["runtime"],
        columns=columns,
        rows=rows,
    )


def run_dbapi_probe(
    probe: DifferentialProbe,
    *,
    engine: str,
    connection: Any,
    runtime: dict[str, Any],
) -> dict[str, object]:
    statement = validate_readonly_sql(probe.sql)
    cursor = connection.cursor()
    try:
        cursor.execute(statement)
        rows = cursor.fetchmany(MAX_PROBE_ROWS + 1)
        if len(rows) > MAX_PROBE_ROWS:
            raise ValueError("DIFFERENTIAL_PROBE_ROW_LIMIT_EXCEEDED")
        columns = [str(column[0]) for column in (cursor.description or ())]
        return _engine_success(
            engine=engine,
            runtime=runtime,
            columns=columns,
            rows=rows,
        )
    except ValueError:
        raise
    except Exception as exc:
        return _engine_error(engine=engine, runtime=runtime, exc=exc)
    finally:
        cursor.close()


def _comparison_outcome(
    engine_results: list[dict[str, object]],
    projection_key: str,
) -> str:
    successful = [
        result
        for result in engine_results
        if result["status"] == "PASS"
    ]
    if len(successful) < 2:
        return "INSUFFICIENT_SUCCESSFUL_ENGINES"

    first = successful[0][projection_key]
    if all(result[projection_key] == first for result in successful[1:]):
        return "AGREE"
    return "DIVERGE"


def _execution_outcome(engine_results: list[dict[str, object]]) -> str:
    successful = sum(result["status"] == "PASS" for result in engine_results)
    if successful == len(engine_results):
        return "ALL_PASS"
    if successful == 0:
        return "ALL_ERROR"
    return "MIXED_PASS_ERROR"


def _pairwise_evidence(engine_results: list[dict[str, object]]) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for index, left in enumerate(engine_results):
        for right in engine_results[index + 1:]:
            left_pass = left["status"] == "PASS"
            right_pass = right["status"] == "PASS"
            if left_pass and right_pass:
                execution = "BOTH_PASS"
                value = (
                    "AGREE"
                    if left["value_projection"] == right["value_projection"]
                    else "DIVERGE"
                )
                types = (
                    "AGREE"
                    if left["type_projection"] == right["type_projection"]
                    else "DIVERGE"
                )
            elif left_pass != right_pass:
                execution = "PASS_ERROR_DIVERGENCE"
                value = "NOT_COMPARABLE"
                types = "NOT_COMPARABLE"
            else:
                execution = "BOTH_ERROR"
                value = "NOT_COMPARABLE"
                types = "NOT_COMPARABLE"
            pairs.append(
                {
                    "left_engine": left["engine"],
                    "right_engine": right["engine"],
                    "execution": execution,
                    "value": value,
                    "type": types,
                }
            )
    return pairs


def run_differential_conformance(
    *,
    settings: Settings | None = None,
    probes: Iterable[DifferentialProbe] = DEFAULT_PROBES,
    source_commit: str | None = None,
    dbapi_engines: Mapping[str, tuple[Any, dict[str, Any]]] | None = None,
) -> dict[str, object]:
    corpus = tuple(probes)
    if not corpus:
        raise ValueError("DIFFERENTIAL_PROBE_CORPUS_EMPTY")
    if len(corpus) > MAX_PROBES:
        raise ValueError("DIFFERENTIAL_PROBE_COUNT_EXCEEDED")

    probe_ids = [probe.probe_id for probe in corpus]
    if len(set(probe_ids)) != len(probe_ids):
        raise ValueError("DIFFERENTIAL_PROBE_ID_DUPLICATE")

    default_corpus = corpus == DEFAULT_PROBES
    corpus_origin = (
        "DEFAULT_SOURCE_CONTROLLED"
        if default_corpus
        else "BOUNDED_LIBRARY_INPUT"
    )
    evidence_scope = (
        "FIXED_SOURCE_CONTROLLED_PROBES_ONLY"
        if default_corpus
        else "BOUNDED_PROBE_SET_ONLY"
    )

    postgres_runtime: dict[str, Any] | None = None
    if settings is not None:
        postgres_runtime = platform_health(settings)["runtime"]

    results: list[dict[str, object]] = []
    for probe in corpus:
        engines = [
            _run_duckdb_probe(probe),
            _run_sqlite_probe(probe),
        ]

        if settings is not None:
            assert postgres_runtime is not None
            engines.append(_run_postgresql_probe(probe, settings, postgres_runtime))
        else:
            engines.append(
                {
                    "engine": "postgresql",
                    "status": "NOT_RUN",
                    "reason": "POSTGRESQL_SETTINGS_NOT_SUPPLIED",
                }
            )

        for engine, (connection, runtime) in (dbapi_engines or {}).items():
            engines.append(
                run_dbapi_probe(
                    probe,
                    engine=engine,
                    connection=connection,
                    runtime=runtime,
                )
            )

        participating = [
            result for result in engines if result["status"] != "NOT_RUN"
        ]
        results.append(
            {
                "probe": probe.as_dict(),
                "engines": engines,
                "execution_outcome": _execution_outcome(participating),
                "value_outcome": _comparison_outcome(
                    participating,
                    "value_projection",
                ),
                "type_outcome": _comparison_outcome(
                    participating,
                    "type_projection",
                ),
                "pairwise_evidence": _pairwise_evidence(participating),
                "evidence_scope": evidence_scope,
                "behavioral_equivalence": "NOT_ESTABLISHED",
            }
        )

    subject = {
        "corpus_digest": canonical_digest([probe.as_dict() for probe in corpus]),
        "result_digest": canonical_digest(results),
        "postgresql_included": settings is not None,
        "dbapi_engines_included": sorted((dbapi_engines or {}).keys()),
        "probe_count": len(corpus),
        "source_commit": source_commit,
        "corpus_origin": corpus_origin,
    }

    return {
        "schema": "SQL_CONNECTOME_DIFFERENTIAL_CONFORMANCE_V1",
        "source_commit": source_commit,
        "probe_count": len(corpus),
        "postgresql_included": settings is not None,
        "dbapi_engines_included": sorted((dbapi_engines or {}).keys()),
        "corpus_origin": corpus_origin,
        "evidence_scope": evidence_scope,
        "generalization": "NOT_ESTABLISHED",
        "behavioral_equivalence": "NOT_ESTABLISHED",
        "results": results,
        "receipt": make_receipt("DIFFERENTIAL_CONFORMANCE", subject),
    }
