from __future__ import annotations

from .connectivity import ConnectionIdentity, EffectClass
from .session_attestation import SessionAttestation, validate_session_attestation
from .cross_bound_receipts import (
    CrossBoundReceipt,
    CurrentnessState,
    TransitionKind,
    make_cross_bound_receipt,
)


def understand_receipt(
    input_digest: str, output_digest: str, **kwargs: object
) -> CrossBoundReceipt:
    return make_cross_bound_receipt(
        TransitionKind.UNDERSTAND,
        input_digests=(input_digest,),
        output_digests=(output_digest,),
        **kwargs,
    )


def bind_receipt(
    input_digest: str,
    output_digest: str,
    *,
    upstream: tuple[CrossBoundReceipt, ...],
    **kwargs: object,
) -> CrossBoundReceipt:
    return make_cross_bound_receipt(
        TransitionKind.BIND,
        input_digests=(input_digest,),
        output_digests=(output_digest,),
        upstream=upstream,
        **kwargs,
    )


def translate_receipt(
    input_digest: str,
    output_digest: str,
    *,
    upstream: tuple[CrossBoundReceipt, ...],
    **kwargs: object,
) -> CrossBoundReceipt:
    return make_cross_bound_receipt(
        TransitionKind.TRANSLATE,
        input_digests=(input_digest,),
        output_digests=(output_digest,),
        upstream=upstream,
        **kwargs,
    )


def validate_receipt(
    input_digest: str,
    output_digest: str,
    *,
    upstream: tuple[CrossBoundReceipt, ...],
    **kwargs: object,
) -> CrossBoundReceipt:
    return make_cross_bound_receipt(
        TransitionKind.VALIDATE,
        input_digests=(input_digest,),
        output_digests=(output_digest,),
        upstream=upstream,
        **kwargs,
    )


def execute_receipt(
    input_digest: str,
    output_digest: str,
    *,
    upstream: tuple[CrossBoundReceipt, ...],
    effect: EffectClass,
    connection_identity: ConnectionIdentity,
    authorization_receipt: str | None = None,
    currentness: CurrentnessState = CurrentnessState.UNKNOWN,
    session_attestation: SessionAttestation | None = None,
    **kwargs: object,
) -> CrossBoundReceipt:
    evidence_refs = tuple(kwargs.pop("evidence_refs", ()))
    if currentness is CurrentnessState.CURRENT:
        if session_attestation is None:
            raise ValueError("CURRENT execution requires session re-attestation")
        validate_session_attestation(session_attestation, connection_identity)
        evidence_refs = (*evidence_refs, f"session-attestation:{session_attestation.digest()}")
    return make_cross_bound_receipt(
        TransitionKind.EXECUTE,
        input_digests=(input_digest,),
        output_digests=(output_digest,),
        upstream=upstream,
        effect=effect,
        connection_identity=connection_identity,
        authorization_receipt=authorization_receipt,
        currentness=currentness,
        evidence_refs=evidence_refs,
        **kwargs,
    )
