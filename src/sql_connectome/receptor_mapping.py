from __future__ import annotations

from .receptor_capabilities import KNOWN_LOSS_MARKERS, SUPPORTED_CONSTRUCTS
from .receptors import ExternalPlan, MappingState, ReceptorMapping, external_plan_digest


def map_external_plan(
    plan: ExternalPlan, *, logical_plan_digest: str | None = None
) -> ReceptorMapping:
    supported_set = SUPPORTED_CONSTRUCTS[plan.language]
    supported = tuple(item for item in plan.constructs if item in supported_set)
    unsupported = tuple(item for item in plan.constructs if item not in supported_set)
    losses = tuple(
        KNOWN_LOSS_MARKERS[plan.language].get(
            item, f"{plan.language.value}_{item}_UNSUPPORTED_V1"
        )
        for item in unsupported
    )
    if unsupported and supported:
        state = MappingState.PARTIAL
    elif unsupported:
        state = MappingState.UNSUPPORTED
    else:
        state = MappingState.FULL
    if state is not MappingState.FULL:
        logical_plan_digest = None
    return ReceptorMapping(
        receptor_version="v1",
        external_plan_digest=external_plan_digest(plan),
        state=state,
        supported_constructs=supported,
        unsupported_constructs=unsupported,
        semantic_losses=losses,
        logical_plan_digest=logical_plan_digest,
    )
