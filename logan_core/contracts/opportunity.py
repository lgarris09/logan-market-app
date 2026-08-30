from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .personal_relevance import PersonalRelevanceResult


class Dimensions(BaseModel):
    personal_relevance: float = Field(ge=0.0, le=1.0)
    global_importance: float = Field(ge=0.0, le=1.0)
    community_momentum: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    opportunity_magnitude: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)
    actionability: float = Field(ge=0.0, le=1.0)
    connection_strength: float = Field(ge=0.0, le=1.0)


class AttentionRecommendation(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    recommend: bool
    dimensions: Dimensions
    # Renamed from priority_score (ADR-029, V3.1.4 BATCH-1 Stage 3).
    # INTERNAL-ONLY: never returned via any public API response, never used
    # for recommend/suppress gating beyond this engine's own threshold check,
    # never becomes Opportunity confidence. Used solely for internal
    # operational ordering (e.g. sort/notification-queue tie-breaking).
    # Public-facing ordering must use a derived ordinal (e.g. rank position
    # in an already-sorted response), never this raw value. See
    # docs/DECISIONS.md ADR-029 and 07_DATA_CONTRACTS.md.
    internal_rank_score: float = Field(ge=0.0, le=1.0)
    # V2.3B Phase 2 -- the structured, explainable basis for
    # dimensions.personal_relevance above (see
    # logan_core/opportunity/personal_relevance.py). Optional/None only for
    # any pre-Phase-2 direct construction that doesn't supply one; every real
    # OpportunityEngine.evaluate() call populates it.
    personal_relevance_result: Optional[PersonalRelevanceResult] = None
    reasons: list[str] = Field(default_factory=list)
    competing_items: list[UUID] = Field(default_factory=list)
    recommended_at: datetime
    decision_trace: list = Field(default_factory=list)
