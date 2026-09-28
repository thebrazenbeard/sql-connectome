from sql_connectome.engine_validation import (
    EngineRuntimeIdentity,
    NativeEngineError,
    ValidationStatus,
    build_engine_validation_result,
)


def test_neutral_validation_receipt_is_deterministic_and_identity_bound() -> None:
    runtime = EngineRuntimeIdentity(
        engine="mysql",
        adapter_id="mysql-v1",
        version="8.4.0",
        facts=(("database", "app"), ("sql_mode", "STRICT_TRANS_TABLES")),
    )
    kwargs = dict(
        runtime=runtime,
        sql="SELECT 1",
        schema_context={"orders": {"id": "INTEGER"}},
        status=ValidationStatus.PASS,
        validation_mode="EXPLAIN_FORMAT_JSON",
        native_payload={"query_block": {"select_id": 1}},
    )
    first = build_engine_validation_result(**kwargs)
    second = build_engine_validation_result(**kwargs)
    assert first.as_dict() == second.as_dict()
    assert first.query_executed is False
    assert first.behavioral_equivalence == "NOT_ESTABLISHED"

    changed = build_engine_validation_result(
        **{**kwargs, "runtime": EngineRuntimeIdentity(
            engine="mysql",
            adapter_id="mysql-v1",
            version="8.4.0",
            facts=(("database", "other"),),
        )}
    )
    assert changed.receipt != first.receipt


def test_native_error_survives_neutral_envelope() -> None:
    error = NativeEngineError(
        error_class="ProgrammingError",
        message="unknown column",
        native_fields=(("code", "1054"), ("sqlstate", "42S22")),
    )
    result = build_engine_validation_result(
        runtime=EngineRuntimeIdentity("mysql", "mysql-v1", "8.4.0"),
        sql="SELECT missing",
        schema_context=None,
        status=ValidationStatus.FAIL,
        validation_mode="EXPLAIN_FORMAT_JSON",
        native_error=error,
    )
    assert result.as_dict()["error"]["native_fields"] == {
        "code": "1054",
        "sqlstate": "42S22",
    }



def test_manifest_keeps_adapter_qualification_independent() -> None:
    from sql_connectome.engine_validation import engine_validation_manifest

    manifest = engine_validation_manifest()
    assert manifest["schema"] == "SQL_CONNECTOME_ENGINE_VALIDATION_MANIFEST_V1"
    assert set(manifest["adapters"]) == {"mysql", "mariadb", "trino"}
    assert all(
        entry["qualification"] == "PROTOCOL_TESTED"
        for entry in manifest["adapters"].values()
    )
    assert "family_qualification" not in manifest



def test_receipt_binds_native_validation_payload() -> None:
    runtime = EngineRuntimeIdentity("mysql", "mysql-v1", "8.4.0")
    first = build_engine_validation_result(
        runtime=runtime,
        sql="SELECT 1",
        schema_context=None,
        status=ValidationStatus.PASS,
        validation_mode="EXPLAIN_FORMAT_JSON",
        native_payload={"plan": 1},
    )
    second = build_engine_validation_result(
        runtime=runtime,
        sql="SELECT 1",
        schema_context=None,
        status=ValidationStatus.PASS,
        validation_mode="EXPLAIN_FORMAT_JSON",
        native_payload={"plan": 2},
    )
    assert first.receipt != second.receipt
