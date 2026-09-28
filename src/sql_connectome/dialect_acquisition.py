from __future__ import annotations

from .dialect_genome import DialectObservation, EvidenceClass, EvidenceCurrentness


def dependency_metadata_observation(**kwargs: object) -> DialectObservation:
    return DialectObservation(evidence_class=EvidenceClass.DEPENDENCY_METADATA, **kwargs)


def official_documentation_observation(**kwargs: object) -> DialectObservation:
    return DialectObservation(evidence_class=EvidenceClass.OFFICIAL_DOCUMENTATION, **kwargs)


def engine_probe_observation(**kwargs: object) -> DialectObservation:
    return DialectObservation(evidence_class=EvidenceClass.ENGINE_PROBE, **kwargs)


__all__ = [
    "EvidenceCurrentness",
    "dependency_metadata_observation",
    "engine_probe_observation",
    "official_documentation_observation",
]
