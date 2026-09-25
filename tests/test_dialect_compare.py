from sql_connectome.connectome import compare_dialects


def test_compare_dialects_reports_bounded_evidence_without_equivalence_claim() -> None:
    result = compare_dialects("postgresql", "sqlite")

    assert result["schema"] == "SQL_CONNECTOME_DIALECT_COMPARISON_V1"
    assert result["source"]["dialect_id"] == "postgresql"
    assert result["target"]["dialect_id"] == "sqlite"
    assert result["source"]["parser_dialect"] == "postgres"
    assert result["target"]["parser_dialect"] == "sqlite"

    capabilities = result["capabilities"]
    assert "json" in capabilities["source_only"]
    assert "stored_procedures" in capabilities["source_only"]
    assert capabilities["target_only"] == []
    assert "relational_select" in capabilities["shared"]

    dimensions = result["semantic_dimensions"]
    assert "document_json" in dimensions["source_only"]
    assert "procedural" in dimensions["source_only"]
    assert "relational" in dimensions["shared"]

    assert isinstance(result["semantic_flags"]["differences"], list)
    assert result["type_graphs"]["source"]["evidence_ceiling"] == "DEPENDENCY_METADATA"
    assert result["type_graphs"]["target"]["evidence_ceiling"] == "DEPENDENCY_METADATA"
    assert len(result["catalog_digest"]) == 64
    assert result["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert result["compatibility_score"] is None
