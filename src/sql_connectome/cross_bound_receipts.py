from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .connectivity import ConnectionIdentity, EffectClass, connection_identity_digest
from .receipts import canonical_digest


class TransitionKind(StrEnum):
    UNDERSTAND = "UNDERSTAND"
    BIND = "BIND"
    TRANSLATE = "TRANSLATE"
    VALIDATE = "VALIDATE"
    EXECUTE = "EXECUTE"


class CurrentnessState(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


_PROTECTED_EFFECTS = {
    EffectClass.MUTATING,
    EffectClass.DDL,
    EffectClass.TRANSACTION_CONTROL,
    EffectClass.UNKNOWN,
}


@dataclass(frozen=True, slots=True)
class AuthorityBinding:
    effect: EffectClass | None = None
    authorization_receipt: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "effect": self.effect.value if self.effect is not None else None,
            "authorization_receipt": self.authorization_receipt,
        }


@dataclass(frozen=True, slots=True)
class CrossBoundReceipt:
    transition: TransitionKind
    input_digests: tuple[str, ...]
    output_digests: tuple[str, ...]
    upstream_receipts: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    implementation_id: str = "sql-connectome"
    semantic_loss_delta: tuple[str, ...] = ()
    accumulated_semantic_loss: tuple[str, ...] = ()
    authority: AuthorityBinding = AuthorityBinding()
    connection_identity_digest: str | None = None
    connection_identity: tuple[tuple[str, Any], ...] = ()
    currentness: CurrentnessState = CurrentnessState.UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "SQL_CONNECTOME_CROSS_BOUND_RECEIPT_V1",
            "transition": self.transition.value,
            "input_digests": list(self.input_digests),
            "output_digests": list(self.output_digests),
            "upstream_receipts": list(self.upstream_receipts),
            "evidence_refs": list(self.evidence_refs),
            "implementation_id": self.implementation_id,
            "semantic_loss_delta": list(self.semantic_loss_delta),
            "accumulated_semantic_loss": list(self.accumulated_semantic_loss),
            "authority": self.authority.as_dict(),
            "connection_identity_digest": self.connection_identity_digest,
            "connection_identity": dict(self.connection_identity),
            "currentness": self.currentness.value,
        }

    def digest(self) -> str:
        return canonical_digest(self.as_dict())


def _stable_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def accumulate_semantic_loss(
    upstream: Iterable[CrossBoundReceipt],
    delta: Iterable[str] = (),
) -> tuple[str, ...]:
    inherited: list[str] = []
    for receipt in upstream:
        inherited.extend(receipt.accumulated_semantic_loss)
    inherited.extend(delta)
    return _stable_unique(inherited)


def _identity_snapshot(identity: ConnectionIdentity | None) -> tuple[tuple[str, Any], ...]:
    if identity is None:
        return ()
    return tuple(identity.as_dict().items())


def make_cross_bound_receipt(
    transition: TransitionKind,
    *,
    input_digests: tuple[str, ...],
    output_digests: tuple[str, ...],
    upstream: tuple[CrossBoundReceipt, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    implementation_id: str = "sql-connectome",
    semantic_loss_delta: tuple[str, ...] = (),
    effect: EffectClass | None = None,
    authorization_receipt: str | None = None,
    connection_identity: ConnectionIdentity | None = None,
    currentness: CurrentnessState = CurrentnessState.UNKNOWN,
) -> CrossBoundReceipt:
    if transition is TransitionKind.EXECUTE and effect in _PROTECTED_EFFECTS:
        if not authorization_receipt:
            raise PermissionError(f"{effect.value} requires an external authorization receipt")
    return CrossBoundReceipt(
        transition=transition,
        input_digests=input_digests,
        output_digests=output_digests,
        upstream_receipts=tuple(receipt.digest() for receipt in upstream),
        evidence_refs=evidence_refs,
        implementation_id=implementation_id,
        semantic_loss_delta=semantic_loss_delta,
        accumulated_semantic_loss=accumulate_semantic_loss(upstream, semantic_loss_delta),
        authority=AuthorityBinding(effect, authorization_receipt),
        connection_identity_digest=(
            connection_identity_digest(connection_identity) if connection_identity else None
        ),
        connection_identity=_identity_snapshot(connection_identity),
        currentness=currentness,
    )


def cross_bound_receipt_digest(receipt: CrossBoundReceipt) -> str:
    return receipt.digest()


def validate_receipt_chain(
    receipt: CrossBoundReceipt,
    upstream: tuple[CrossBoundReceipt, ...],
) -> None:
    expected_upstream = tuple(item.digest() for item in upstream)
    if receipt.upstream_receipts != expected_upstream:
        raise ValueError("upstream receipt binding mismatch")
    expected_loss = accumulate_semantic_loss(upstream, receipt.semantic_loss_delta)
    if receipt.accumulated_semantic_loss != expected_loss:
        raise ValueError("accumulated semantic loss mismatch")
    if receipt.connection_identity:
        snapshot = dict(receipt.connection_identity)
        if receipt.connection_identity_digest != canonical_digest(snapshot):
            raise ValueError("connection identity binding mismatch")
