from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import Reference


class ReasoningResult(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    significance: str
    # Renamed from `personal_relevance` per ADR-021 — do not confuse with the
    # float-typed Dimensions.personal_relevance used by the Opportunity Engine.
    personal_relevance_narrative: str
    connected_entities: list[str] = Field(default_factory=list)
    # Explicit/inferred split of connected_entities above (union of the two,
    # unchanged) -- lets the Opportunity Engine bound an inferred-only
    # connection's relevance contribution below an explicit one (holdings or
    # Interest(source="explicit")) rather than treating them identically.
    # Additive fields, both default empty -- existing callers that only read
    # connected_entities are unaffected.
    connected_entities_explicit: list[str] = Field(default_factory=list)
    connected_entities_inferred: list[str] = Field(default_factory=list)
    # Sprint 3.6.7 Block 3 -- additive, default 0.0: the strongest matched
    # inferred Interest.weight among connected_entities_inferred (0.0 when
    # empty). Lets the Opportunity Engine's "connect" step scale an
    # inferred-only connection's relevance with how mature the underlying
    # behavioral evidence actually is, instead of a flat floor regardless of
    # evidence strength -- see OpportunityEngine's _scale_inferred_relevance
    # and docs/DECISIONS.md's Sprint 3.6.7 Block 3 ADR. Every existing
    # caller/test that doesn't populate this field gets exactly the same
    # flat 0.5 floor as before (see that function's own docstring).
    inferred_relevance_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    # V2.3B Phase 2 (Learning-Driven STRATUS) -- additive, default-safe fields
    # for Personal Relevance V2 (see logan_core/opportunity/personal_relevance.py).
    # `is_watched`: this user's *current* Watch state for this entity, read
    # directly (like holdings/explicit interests) rather than folded through
    # MemoryStore's MIN_REPEAT_EVIDENCE evidence pool -- a single explicit
    # Watch action is a standalone, deliberate signal, not something that
    # needs a second corroborating observation to count. Removing a Watch
    # simply stops this being true on the next poll; it never rewrites or
    # deletes the historical feedback_record the original watch action wrote.
    is_watched: bool = False
    # `inferred_evidence_count`/`inferred_last_reinforced`: the matched
    # inferred Interest's paired BehaviorPattern provenance (evidence_count,
    # last_reinforced) for connected_entities_inferred -- lets Personal
    # Relevance V2's explanation distinguish "returned to this many times
    # recently" from "one thin, just-qualifying observation" instead of only
    # ever seeing the single scalar Interest.weight. 0/None when there is no
    # inferred connection, matching inferred_relevance_strength's own default.
    inferred_evidence_count: int = Field(default=0, ge=0)
    inferred_last_reinforced: Optional[datetime] = None
    prior_signal_links: list[UUID] = Field(default_factory=list)
    stance: Literal["confirms", "contradicts", "complicates", "new"]
    actionability: Literal["actionable", "informational", "ambiguous"]
    explanation: str
    supporting_links: list[Reference] = Field(default_factory=list)
    reasoned_at: datetime
    decision_trace: list = Field(default_factory=list)
