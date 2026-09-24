from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import SemanticDimension


@dataclass(frozen=True, slots=True)
class IRNode:
    node_id: str
    kind: str
    attributes: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class IREdge:
    source: str
    target: str
    relation: str
    attributes: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class TranslationLoss:
    kind: str
    description: str
    source_fragment: str | None = None


@dataclass(frozen=True, slots=True)
class SQLSemanticIR:
    """Dialect-independent semantic graph envelope.

    The IR intentionally does not force every SQL family into one lowest-common-
    denominator AST. Dialect-specific semantics may survive as typed nodes,
    edges, capabilities, or extensions until a target can represent or reject them.
    """

    operation: str
    source_dialect: str
    source_version: str | None = None
    roots: tuple[str, ...] = ()
    nodes: tuple[IRNode, ...] = ()
    edges: tuple[IREdge, ...] = ()
    semantic_dimensions: frozenset[SemanticDimension] = field(default_factory=frozenset)
    required_capabilities: frozenset[str] = field(default_factory=frozenset)
    input_relations: tuple[str, ...] = ()
    output_fields: tuple[str, ...] = ()
    type_constraints: tuple[str, ...] = ()
    side_effects: frozenset[str] = field(default_factory=frozenset)
    semantic_extensions: tuple[tuple[str, Any], ...] = ()
    provenance: tuple[str, ...] = ()
    translation_loss: tuple[TranslationLoss, ...] = ()

    def validate_graph(self) -> None:
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("DUPLICATE_IR_NODE_ID")

        known = set(node_ids)
        dangling = [
            edge
            for edge in self.edges
            if edge.source not in known or edge.target not in known
        ]
        if dangling:
            raise ValueError("DANGLING_IR_EDGE")

        unknown_roots = [root for root in self.roots if root not in known]
        if unknown_roots:
            raise ValueError("UNKNOWN_IR_ROOT")

    @property
    def is_effect_free(self) -> bool:
        return not self.side_effects
