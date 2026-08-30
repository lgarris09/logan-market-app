from typing import Literal

from pydantic import BaseModel, Field


class PersonalRelevanceResult(BaseModel):
    """V2.3B Phase 2 (Learning-Driven STRATUS) -- the deliberate, explainable
    replacement for the old inline personal_relevance computation
    (logan_core/opportunity/engine.py). Produced by
    logan_core/opportunity/personal_relevance.py's compute_personal_relevance(),
    the sole place this is derived (per "only the Opportunity Engine
    scores/ranks") -- never re-derived downstream.

    `value` is the same bounded [0,1] number that feeds Dimensions.
    personal_relevance (never a second, independent score) -- kept here too
    so a caller with a legitimate reason (internal diagnostics, the Learning
    Decision Report) doesn't need to reach into Dimensions separately. Per
    ADR-029's discipline for internal_rank_score, this raw float is not
    something the public API/mobile contract exposes on its own -- only
    `state`/`basis`/`strongest_signals`/`not_contributing`/`explanation` are
    meant to reach a consumer-facing surface.
    """

    schema_version: str = "1.0"
    value: float = Field(ge=0.0, le=1.0)
    # Consumer-safe qualitative bucket -- the thing actually safe to expose,
    # unlike the raw float.
    state: Literal["high", "moderate", "low", "unknown"]
    # The strongest basis that won -- explicit priority order is watch >
    # explicit > inferred > none, matching compute_personal_relevance()'s own
    # decision order.
    basis: Literal["explicit", "watch", "inferred", "none"]
    is_watched: bool = False
    # Only meaningful when basis == "inferred" -- the matched BehaviorPattern's
    # own evidence_count/last_reinforced (see ReasoningResult's identically-
    # named fields) surfaced here so the "why relevant" explanation can cite a
    # real number rather than a bare qualitative claim.
    evidence_count: int = Field(default=0, ge=0)
    explicit: bool = False
    strongest_signals: list[str] = Field(default_factory=list)
    not_contributing: list[str] = Field(default_factory=list)
    # One deterministic, template-generated sentence -- never LLM-authored --
    # summarizing the above for a "why this matters to you" surface.
    explanation: str
