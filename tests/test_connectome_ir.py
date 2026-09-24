import pytest

from sql_connectome.connectome import IREdge, IRNode, SemanticDimension, SQLSemanticIR


def test_semantic_ir_accepts_typed_graph() -> None:
    ir = SQLSemanticIR(
        operation="select",
        source_dialect="postgresql",
        roots=("select",),
        nodes=(
            IRNode("select", "SELECT"),
            IRNode("limit", "ROW_LIMIT", (("count", 10),)),
        ),
        edges=(IREdge("select", "limit", "CONSTRAINED_BY"),),
        semantic_dimensions=frozenset({SemanticDimension.RELATIONAL}),
        required_capabilities=frozenset({"relational_select"}),
    )

    ir.validate_graph()
    assert ir.is_effect_free is True


def test_semantic_ir_rejects_dangling_edges() -> None:
    ir = SQLSemanticIR(
        operation="select",
        source_dialect="unknown",
        nodes=(IRNode("select", "SELECT"),),
        edges=(IREdge("select", "missing", "ROUTES_TO"),),
    )

    with pytest.raises(ValueError, match="DANGLING_IR_EDGE"):
        ir.validate_graph()


def test_semantic_ir_rejects_duplicate_node_ids() -> None:
    ir = SQLSemanticIR(
        operation="select",
        source_dialect="unknown",
        nodes=(IRNode("x", "SELECT"), IRNode("x", "ROW_LIMIT")),
    )

    with pytest.raises(ValueError, match="DUPLICATE_IR_NODE_ID"):
        ir.validate_graph()
