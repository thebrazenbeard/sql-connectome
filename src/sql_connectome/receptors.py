from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .receipts import canonical_digest


class ReceptorLanguage(StrEnum):
    PRQL = "PRQL"
    CYPHER = "CYPHER"
    SPARQL = "SPARQL"
    DATAFRAME = "DATAFRAME"


class ReceptorState(StrEnum):
    EXACT_SUBSET = "EXACT_SUBSET"
    LOSSY_SUBSET = "LOSSY_SUBSET"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ReceptorMapping:
    language: ReceptorLanguage
    source_construct: str
    target_operator: str | None
    state: ReceptorState
    semantic_losses: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    receptor_version: str = "v1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_RECEPTOR_MAPPING_V1",
            "language": self.language.value,
            "source_construct": self.source_construct,
            "target_operator": self.target_operator,
            "state": self.state.value,
            "semantic_losses": list(self.semantic_losses),
            "evidence_refs": list(self.evidence_refs),
            "receptor_version": self.receptor_version,
            "authority": "REPRESENTABILITY_EVIDENCE_ONLY",
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


_CATALOG: dict[tuple[ReceptorLanguage, str], tuple[str | None, ReceptorState, tuple[str, ...]]] = {
    (ReceptorLanguage.PRQL, "from"): ("READ", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.PRQL, "filter"): ("FILTER", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.PRQL, "select"): ("PROJECT", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.PRQL, "take"): ("LIMIT", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.DATAFRAME, "scan"): ("READ", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.DATAFRAME, "filter"): ("FILTER", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.DATAFRAME, "select"): ("PROJECT", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.DATAFRAME, "groupby"): ("AGGREGATE", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.CYPHER, "match"): (
        "JOIN",
        ReceptorState.LOSSY_SUBSET,
        ("GRAPH_PATTERN_TO_RELATIONAL_JOIN_LOSS",),
    ),
    (ReceptorLanguage.CYPHER, "return"): ("PROJECT", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.CYPHER, "variable_length_path"): (
        None,
        ReceptorState.UNSUPPORTED,
        ("RECURSIVE_GRAPH_PATH_NOT_MODELED",),
    ),
    (ReceptorLanguage.SPARQL, "basic_graph_pattern"): (
        "JOIN",
        ReceptorState.LOSSY_SUBSET,
        ("RDF_TERM_AND_GRAPH_SEMANTICS_NOT_MODELED",),
    ),
    (ReceptorLanguage.SPARQL, "filter"): ("FILTER", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.SPARQL, "project"): ("PROJECT", ReceptorState.EXACT_SUBSET, ()),
    (ReceptorLanguage.SPARQL, "property_path"): (
        None,
        ReceptorState.UNSUPPORTED,
        ("SPARQL_PROPERTY_PATH_NOT_MODELED",),
    ),
}


def map_receptor_construct(
    language: ReceptorLanguage,
    source_construct: str,
    *,
    evidence_refs: tuple[str, ...] = (),
) -> ReceptorMapping:
    key = (language, source_construct.strip().lower())
    target, state, losses = _CATALOG.get(
        key, (None, ReceptorState.UNKNOWN, ("NO_V1_RECEPTOR_MAPPING",))
    )
    return ReceptorMapping(
        language,
        key[1],
        target,
        state,
        losses,
        evidence_refs,
    )
