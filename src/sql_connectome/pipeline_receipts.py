from __future__ import annotations

from .connectivity import ConnectionIdentity, EffectClass
from .cross_bound_receipts import (
    CrossBoundReceipt,
    CurrentnessState,
    TransitionKind,
    make_cross_bound_receipt,
)


def understand_receipt(input_digest: str, output_digest: str, **kwargs: object) -> CrossBoundReceipt:
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
    **kwargs: object,
) -> CrossBoundReceipt:
    return make_cross_bound_receipt(
        TransitionKind.EXECUTE,
        input_digests=(input_digest,),
        output_digests=(output_digest,),
        upstream=upstream,
        effect=effect,
        connection_identity=connection_identity,
        authorization_receipt=authorization_receipt,
        currentness=currentness,
        **kwargs,
    )
