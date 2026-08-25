"""Sprint 3.6.7 Block 4 -- authoritative, server-side opportunity context for
contextual Ask STRATUS. `OpportunityContext` is a snapshot of exactly the
real, already-computed fields a grounded answer needs (DeliveredItem's
narrative text, ConclusionConfidence's classification/limiting_factors/
alternatives, the entity's attached TriggerEvents, and Dimensions'
personal-relevance breakdown) -- never internal-only fields (ADR-029:
internal_rank_score must never reach any public surface, including this
one).

Built once per `_run_feed_pipeline()` call (backend/app/logan_feed.py) from
the same `PipelineResult` that already produces each request's `FeedItem`s --
this is not a second, independent computation of opportunity state, just a
retained, richer slice of the one the pipeline already produced. Process-
lifetime only, like every other piece of live opportunity state in this
backend (`_orchestrator`, `_user_model`) -- a backend restart clears it, same
limitation, same reason (ADR-006 remains open on durable per-request state).
"""

import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import Domain  # noqa: E402
from logan_core.convergence import STOCK_CONVERGENCE_MULTI_SOURCE  # noqa: E402
from logan_core.orchestrator.pipeline import PipelineResult  # noqa: E402


class OpportunityContext(BaseModel):
    event_id: UUID
    entity_id: str
    display_name: str
    domain: Domain
    headline: str
    what_happened: str
    why_it_matters: str
    why_it_matters_to_me: str
    why_now: str
    confidence_score: float
    confidence_label: str
    classification: str
    limiting_factors: list[str]
    alternatives: list[str]
    # Every distinct trigger_code currently attached to this entity's
    # coherent opportunity (see orchestrator/pipeline.py's
    # _merge_entity_events, Sprint 3.6.7 Block 2) -- real fired triggers,
    # never fabricated ones.
    trigger_codes: list[str]
    # Populated only when STOCK_CONVERGENCE_MULTI_SOURCE is among
    # trigger_codes -- the real distinct signal_types StockConvergenceTracker
    # found converging (see its own `context["sources"]`). Empty otherwise --
    # never implies convergence that didn't actually fire.
    convergence_sources: list[str]
    personal_relevance: float
    # "explicit" | "inferred" | "none" -- which kind of connection (if any)
    # drove personal_relevance, mirroring ReasoningEngine's own
    # connected_entities_explicit/_inferred split (ADR-048).
    connection_basis: str
    is_new_for_user: bool

    # Stock Opportunity Logic V2 (see docs/DECISIONS.md's Sprint 3.6.9 ADR).
    # All None/False when lifecycle tracking isn't active for this call
    # (demo mode, no live tickers configured) -- additive, never required.
    # This is what lets a grounded LLM answer describe a *delta* ("no
    # material change since the earnings beat -- still monitoring") instead
    # of restating the original card every time, per the ADR's explicit
    # repeated-card product fix; build_system_prompt (ask_llm_provider.py)
    # is the only place these are ever turned into model-facing text, and
    # only ever as authoritative, already-computed facts -- the model never
    # decides any of these values itself.
    lifecycle_state: Optional[str] = None
    meaningful_change_type: Optional[str] = None
    lifecycle_reason: Optional[str] = None
    thesis_age_hours: Optional[float] = None
    is_meaningful_update: bool = False


def build_opportunity_context(
    entity_id: str,
    display_name: str,
    result: "PipelineResult",
    is_new_for_user: bool,
) -> OpportunityContext:
    delta = result.lifecycle_delta
    trigger_codes = sorted({t.trigger_code for t in result.event.trigger_events})

    convergence_sources: list[str] = []
    for trigger in result.event.trigger_events:
        if trigger.trigger_code == STOCK_CONVERGENCE_MULTI_SOURCE:
            sources = trigger.context.get("sources")
            if isinstance(sources, list):
                convergence_sources = [str(s) for s in sources]
            break

    connection_basis = "none"
    if result.reasoning.connected_entities_explicit:
        connection_basis = "explicit"
    elif result.reasoning.connected_entities_inferred:
        connection_basis = "inferred"

    return OpportunityContext(
        event_id=result.event.event_id,
        entity_id=entity_id,
        display_name=display_name,
        domain=result.event.domain,
        headline=result.delivered_item.headline,
        what_happened=result.delivered_item.what_happened,
        why_it_matters=result.delivered_item.why_it_matters,
        why_it_matters_to_me=result.delivered_item.why_it_matters_to_me,
        why_now=result.delivered_item.why_now,
        confidence_score=result.confidence.confidence_score,
        confidence_label=result.delivered_item.confidence_label,
        classification=result.confidence.classification,
        limiting_factors=list(result.confidence.limiting_factors),
        alternatives=list(result.confidence.alternatives),
        trigger_codes=trigger_codes,
        convergence_sources=convergence_sources,
        personal_relevance=result.recommendation.dimensions.personal_relevance,
        connection_basis=connection_basis,
        is_new_for_user=is_new_for_user,
        lifecycle_state=delta.new_state if delta else None,
        meaningful_change_type=delta.change_type if delta else None,
        lifecycle_reason=delta.reason if delta else None,
        thesis_age_hours=delta.thesis_age_hours if delta else None,
        is_meaningful_update=delta.is_meaningful if delta else False,
    )


class OpportunityContextCache:
    """Process-lifetime, bounded cache of the most recently computed
    OpportunityContext per event_id -- the "authoritative rehydration"
    lookup contextual Ask STRATUS uses. Not a general-purpose store: entirely
    replaced/refreshed on every `_run_feed_pipeline()` call (see
    logan_feed.py), never written to from anywhere else. Bounded by simply
    never growing past the current poll's item count (a fresh dict each
    refresh, not an ever-growing accumulation) -- no separate eviction policy
    needed.
    """

    def __init__(self) -> None:
        self._by_event_id: dict[UUID, OpportunityContext] = {}

    def replace_all(self, contexts: list[OpportunityContext]) -> None:
        self._by_event_id = {c.event_id: c for c in contexts}

    def get(self, event_id: UUID) -> Optional[OpportunityContext]:
        return self._by_event_id.get(event_id)
