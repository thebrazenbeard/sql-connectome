import pytest

from sql_connectome.connectome import SQLTextError, parse_sql_text, text_pipeline


def test_semantic_parser_rejects_oversized_text(monkeypatch) -> None:
    monkeypatch.setattr(text_pipeline, "MAX_SQL_TEXT_CHARS", 20)

    with pytest.raises(SQLTextError, match="SQL_TEXT_TOO_LARGE"):
        parse_sql_text("SELECT " + ", ".join(str(i) for i in range(20)), "postgresql")


def test_semantic_parser_rejects_ast_over_node_ceiling(monkeypatch) -> None:
    monkeypatch.setattr(text_pipeline, "MAX_SQL_AST_NODES", 4)

    with pytest.raises(SQLTextError, match="Maximum number of AST nodes"):
        parse_sql_text("SELECT 1 + 2 + 3 + 4 + 5", "postgresql")


def test_normal_query_remains_below_default_resource_limits() -> None:
    analysis = parse_sql_text("SELECT id FROM users WHERE id = 1", "postgresql")

    assert analysis.ir.operation == "SELECT"
