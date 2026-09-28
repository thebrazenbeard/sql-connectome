from sql_connectome.connectivity import ConnectionIdentity, EffectClass
from sql_connectome.cross_bound_receipts import CurrentnessState, validate_receipt_chain
from sql_connectome.pipeline_receipts import (
    bind_receipt,
    execute_receipt,
    translate_receipt,
    understand_receipt,
    validate_receipt,
)
from sql_connectome.receipts import make_receipt


def test_complete_pipeline_forms_valid_receipt_dag() -> None:
    understand = understand_receipt("source", "ir", semantic_loss_delta=("SOURCE_UNKNOWN",))
    bind = bind_receipt("ir", "bound", upstream=(understand,))
    translate = translate_receipt("bound", "sql", upstream=(bind,), evidence_refs=("dialect:v1",))
    validate = validate_receipt("sql", "validated", upstream=(translate,))
    identity = ConnectionIdentity(
        provider="sqlite",
        engine="sqlite",
        engine_version="3",
        transport_family="dbapi",
        transport_implementation="sqlite3",
        catalog="main",
        session_facts=(("mode", "isolated"),),
    )
    execute = execute_receipt(
        "validated",
        "result",
        upstream=(validate,),
        effect=EffectClass.READ_ONLY,
        connection_identity=identity,
        currentness=CurrentnessState.CURRENT,
    )
    validate_receipt_chain(bind, (understand,))
    validate_receipt_chain(translate, (bind,))
    validate_receipt_chain(validate, (translate,))
    validate_receipt_chain(execute, (validate,))
    assert execute.accumulated_semantic_loss == ("SOURCE_UNKNOWN",)


def test_legacy_receipt_schema_remains_unchanged() -> None:
    receipt = make_receipt("legacy", {"value": 1}, issued_at="2026-01-01T00:00:00+00:00")
    assert receipt["schema"] == "SQL_CONNECTOME_RECEIPT_V1"
    assert receipt["kind"] == "legacy"
