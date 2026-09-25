from __future__ import annotations

import re
from dataclasses import dataclass

from .catalog import DEFAULT_CATALOG, ConnectomeCatalog
from .text_pipeline import (
    SQLTextError,
    _bounded_text,
    _parse_expressions,
    parse_sql_text,
)

_MARKERS: tuple[tuple[str, dict[str, int], str], ...] = (
    (r"\bSELECT\s+TOP\b", {"tsql": 5}, "SELECT TOP"),
    (r"\b(?:CROSS|OUTER)\s+APPLY\b", {"tsql": 5}, "APPLY"),
    (r"\bVARIANT\b", {"snowflake": 5}, "VARIANT"),
    (r"\bCONNECT\s+BY\b", {"oracle": 5, "snowflake": 2}, "CONNECT BY"),
    (
        r"\bQUALIFY\b",
        {"bigquery": 2, "snowflake": 2, "duckdb": 2},
        "QUALIFY",
    ),
    (r"\bENGINE\s*=", {"clickhouse": 5}, "ENGINE clause"),
    (r"\b(?:DISTKEY|SORTKEY)\b", {"redshift": 5}, "Redshift distribution key"),
    (
        r"\bDISTRIBUTE\s+BY\b",
        {"hive": 3, "spark": 3, "databricks": 3},
        "DISTRIBUTE BY",
    ),
    (
        r"\x60[^\x60]+\x60",
        {"mysql": 1, "bigquery": 1, "hive": 1, "spark": 1, "databricks": 1},
        "backtick identifiers",
    ),
    (
        r"::[A-Za-z_]",
        {
            "postgresql": 1,
            "duckdb": 1,
            "materialize": 1,
            "redshift": 1,
            "risingwave": 1,
        },
        "double-colon cast",
    ),
    (
        r"\bUNNEST\s*\(",
        {"bigquery": 1, "trino": 1, "presto": 1, "athena": 1},
        "UNNEST",
    ),
)


@dataclass(frozen=True, slots=True)
class DialectCandidate:
    dialect_id: str
    engine: str
    parser_dialect: str
    score: int
    evidence: tuple[str, ...]
    semantic_admission: str

    def as_dict(self) -> dict[str, object]:
        return {
            "dialect_id": self.dialect_id,
            "engine": self.engine,
            "parser_dialect": self.parser_dialect,
            "score": self.score,
            "evidence": list(self.evidence),
            "semantic_admission": self.semantic_admission,
        }


def _marker_evidence(sql: str, dialect_id: str) -> tuple[int, list[str]]:
    score = 0
    evidence: list[str] = []

    for pattern, weights, description in _MARKERS:
        weight = weights.get(dialect_id)
        if weight and re.search(pattern, sql, flags=re.IGNORECASE):
            score += weight
            evidence.append(f"{description}:+{weight}")

    return score, evidence


def probe_sql_dialects(
    sql: str,
    *,
    max_candidates: int = 8,
    catalog: ConnectomeCatalog = DEFAULT_CATALOG,
) -> dict[str, object]:
    text = _bounded_text(sql)
    if max_candidates < 1 or max_candidates > len(catalog.parser_adapters):
        raise SQLTextError("INVALID_MAX_CANDIDATES")

    candidates: list[DialectCandidate] = []
    parser_failures = 0

    for dialect_id, parser_dialect in sorted(catalog.parser_adapters.items()):
        try:
            expressions = _parse_expressions(text, parser_dialect)
        except SQLTextError:
            parser_failures += 1
            continue

        if len(expressions) != 1:
            continue

        marker_score, evidence = _marker_evidence(text, dialect_id)
        score = 1 + marker_score
        evidence.insert(0, "strict parse:+1")

        try:
            parse_sql_text(text, dialect_id, catalog=catalog)
            semantic_admission = "ADMITTED"
            score += 1
            evidence.append("current semantic genome admits observed capabilities:+1")
        except SQLTextError as exc:
            if str(exc).startswith("SOURCE_CAPABILITY_NOT_ADMITTED:"):
                semantic_admission = "PARTIAL"
            else:
                semantic_admission = "NOT_ADMITTED"

        genome = catalog.dialects[dialect_id]
        candidates.append(
            DialectCandidate(
                dialect_id=dialect_id,
                engine=genome.engine,
                parser_dialect=parser_dialect,
                score=score,
                evidence=tuple(evidence),
                semantic_admission=semantic_admission,
            )
        )

    candidates.sort(key=lambda item: (-item.score, item.dialect_id))
    selected = candidates[:max_candidates]

    top_score = selected[0].score if selected else None
    tied_for_top = (
        len(selected) > 1
        and top_score is not None
        and selected[1].score == top_score
    )

    return {
        "schema": "SQL_CONNECTOME_DIALECT_PROBE_V1",
        "basis": "HEURISTIC_PARSE_AND_MARKER_EVIDENCE",
        "identity_proof": False,
        "ambiguous": not selected or tied_for_top,
        "candidate_count": len(candidates),
        "parser_failure_count": parser_failures,
        "candidates": [candidate.as_dict() for candidate in selected],
    }
