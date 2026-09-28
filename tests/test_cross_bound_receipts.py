import pytest

from sql_connectome.connectivity import ConnectionIdentity, EffectClass
from sql_connectome.cross_bound_receipts import (
    CrossBoundReceipt,
    CurrentnessState,
    TransitionKind,
    make_cross_bound_receipt,
    validate_receipt_chain,
)


def test_transition_digest_is_deterministic_and_binds_artifacts() -> None:
    first = make_cross_bound_receipt(
        TransitionKind.UNDERSTAND, input_digests=("source",), output_digests=("ir",)
    )
    same = make_cross_bound_receipt(
        TransitionKind.UNDERSTAND, input_digests=("source",), output_digests=("ir",)
    )
    changed = make_cross_bound_receipt(
        TransitionKind.UNDERSTAND, input_digests=("source",), output_digests=("other",)
    )
    assert first.digest() == same.digest()
    assert first.digest() != changed.digest()


def test_upstream_evidence_and_loss_are_bound_append_only() -> None:
    first = make_cross_bound_receipt(
        TransitionKind.UNDERSTAND,
        input_digests=("source",),
        output_digests=("ir",),
        semantic_loss_delta=("UNKNOWN_SOURCE_TYPE",),
    )
    second = make_cross_bound_receipt(
        TransitionKind.BIND,
        input_digests=("ir",),
        output_digests=("bound",),
        upstream=(first,),
        evidence_refs=("catalog:1",),
        semantic_loss_delta=("UNRESOLVED_FIELD", "UNKNOWN_SOURCE_TYPE"),
    )
    assert second.accumulated_semantic_loss == (
        "UNKNOWN_SOURCE_TYPE",
        "UNRESOLVED_FIELD",
    )
    validate_receipt_chain(second, (first,))
    with pytest.raises(ValueError):
        validate_receipt_chain(second, ())


def test_chain_validation_rejects_loss_laundering() -> None:
    first = make_cross_bound_receipt(
        TransitionKind.UNDERSTAND,
        input_digests=("source",),
        output_digests=("ir",),
        semantic_loss_delta=("LOSS",),
    )
    valid = make_cross_bound_receipt(
        TransitionKind.BIND,
        input_digests=("ir",),
        output_digests=("bound",),
        upstream=(first,),
    )
    tampered = CrossBoundReceipt(
        transition=valid.transition,
        input_digests=valid.input_digests,
        output_digests=valid.output_digests,
        upstream_receipts=valid.upstream_receipts,
        accumulated_semantic_loss=(),
    )
    with pytest.raises(ValueError):
        validate_receipt_chain(tampered, (first,))


def test_execution_binds_connection_catalog_session_and_currentness() -> None:
    identity = ConnectionIdentity(
        provider="sqlite",
        engine="sqlite",
        engine_version="3",
        transport_family="dbapi",
        transport_implementation="sqlite3",
        catalog="main",
        session_facts=(("mode", "isolated"),),
    )
    receipt = make_cross_bound_receipt(
        TransitionKind.EXECUTE,
        input_digests=("validated",),
        output_digests=("result",),
        effect=EffectClass.READ_ONLY,
        connection_identity=identity,
        currentness=CurrentnessState.UNKNOWN,
    )
    assert dict(receipt.connection_identity)["catalog"] == "main"
    assert receipt.currentness is CurrentnessState.UNKNOWN
    validate_receipt_chain(receipt, ())


def test_protected_execution_requires_external_authorization() -> None:
    with pytest.raises(PermissionError):
        make_cross_bound_receipt(
            TransitionKind.EXECUTE,
            input_digests=("validated",),
            output_digests=("result",),
            effect=EffectClass.DDL,
        )
    receipt = make_cross_bound_receipt(
        TransitionKind.EXECUTE,
        input_digests=("validated",),
        output_digests=("result",),
        effect=EffectClass.DDL,
        authorization_receipt="authorization:external",
    )
    assert receipt.authority.authorization_receipt == "authorization:external"
