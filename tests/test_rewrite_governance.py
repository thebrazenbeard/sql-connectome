from sql_connectome.connectome import (
    RewriteRule,
    TranslationFidelity,
    plan_translation,
    transpile_sql_text,
)
from sql_connectome.connectome.rewrite_governance import govern_translation_plan


def test_constructive_rewrite_has_versioned_governance_evidence() -> None:
    result = transpile_sql_text(
        "SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn FROM users QUALIFY rn = 1",
        "bigquery",
        "postgresql",
    )
    governance = result["rewrite_governance"]
    assert governance["schema"] == "SQL_CONNECTOME_GOVERNED_REWRITE_PLAN_V1"
    assert governance["qualification"] == "CONDITIONAL"
    rewrite = governance["rewrites"][0]
    assert rewrite["rewrite_id"] == "qualify-via-derived-table@1"
    assert rewrite["required_evidence"] == ["CAPABILITY_REGISTRY", "TARGET_PARSE"]
    assert rewrite["observed_evidence"] == ["CAPABILITY_REGISTRY", "TARGET_PARSE"]
    assert rewrite["behavioral_equivalence"] == "NOT_ESTABLISHED"
    assert governance["execution_authority"] == "NONE"
    assert len(governance["digest"]) == 64


def test_unknown_rewrite_rule_fails_closed_as_unqualified() -> None:
    rule = RewriteRule(
        name="invented-rewrite",
        source_capability="qualify",
        target_capabilities=frozenset({"window_functions", "derived_tables"}),
        fidelity=TranslationFidelity.CONSTRUCTIVE,
        description="test-only rewrite without governance evidence",
    )
    plan = plan_translation(
        "bigquery",
        "postgresql",
        {"qualify"},
        rewrite_rules=(rule,),
    )
    governance = govern_translation_plan(
        plan,
        observed_evidence=frozenset({"CAPABILITY_REGISTRY", "TARGET_PARSE"}),
    )
    assert governance["qualification"] == "UNQUALIFIED"
    assert governance["rewrites"][0]["rule_version"] == "UNVERSIONED"
    assert governance["rewrites"][0]["unresolved_semantics"] == [
        "no governed rewrite record"
    ]


def test_no_rewrite_plan_is_qualified_but_does_not_claim_equivalence() -> None:
    result = transpile_sql_text("SELECT 1", "postgresql", "postgresql")
    governance = result["rewrite_governance"]
    assert governance["qualification"] == "QUALIFIED"
    assert governance["rewrites"] == []
    assert governance["behavioral_equivalence"] == "NOT_ESTABLISHED"


def test_missing_required_evidence_fails_closed() -> None:
    result = plan_translation("bigquery", "postgresql", {"qualify"})
    governance = govern_translation_plan(
        result,
        observed_evidence=frozenset({"CAPABILITY_REGISTRY"}),
    )
    assert governance["qualification"] == "UNQUALIFIED"
    rewrite = governance["rewrites"][0]
    assert rewrite["observed_evidence"] == ["CAPABILITY_REGISTRY"]
    assert "missing evidence: TARGET_PARSE" in rewrite["unresolved_semantics"]
