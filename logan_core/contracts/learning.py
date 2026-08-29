from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryWrite(BaseModel):
    schema_version: str = "1.0"
    write_id: UUID
    write_type: Literal[
        "new_record",
        "update_record",
        "decay_update",
        "trust_update",
        "hypothesis_update",
    ]
    target: Literal["memory", "user_model", "trust_registry", "mental_model"]
    content: object
    source_signal: Optional[UUID] = None
    confidence: float = Field(ge=0.0, le=1.0)
    authorized_at: datetime


# V2.3B Personal Learning Phase 1 -- inspection/explainability report, NOT a
# new scoring/ranking concept. Every field here is a plain-language rendering
# of data UserModel/MemoryStore already compute (Interest.weight,
# BehaviorPattern.confidence/evidence_count/last_reinforced,
# UserModel.model_confidence) -- this module never introduces a new score.


class ObservedBehaviorSummary(BaseModel):
    """One raw, factual, uninterpreted observation -- e.g. "Opened NVDA 4
    times." Built directly from feedback_record counts, never from anything
    UserModelBuilder concluded."""

    entity_id: str
    description: str
    count: int = Field(ge=1)


class LearnedTrait(BaseModel):
    """One surviving Interest or BehaviorPattern, explained in plain
    language. Answers, per-trait: what did STRATUS learn, how strong is
    that belief, which observations contributed, when was it last updated,
    is it explicit or inferred, and what would weaken/change it."""

    entity_id: str
    kind: Literal["interest", "behavior"]
    source: Literal["explicit", "inferred"]
    description: str
    strength: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)
    first_learned_at: Optional[datetime] = None
    last_updated_at: datetime
    why: str
    what_would_change_this: str


class NotLearnedTrait(BaseModel):
    """A candidate STRATUS deliberately declined to conclude, and the real,
    specific reason why -- proof this system resists over-inference rather
    than a silent absence."""

    candidate: str
    reason: str


class LearningReport(BaseModel):
    schema_version: str = "1.0"
    user_id: str
    generated_at: datetime
    model_confidence: float = Field(ge=0.0, le=1.0)
    observed: list[ObservedBehaviorSummary] = Field(default_factory=list)
    learned: list[LearnedTrait] = Field(default_factory=list)
    not_learned: list[NotLearnedTrait] = Field(default_factory=list)
    # Honest, standing statements about what this architecture does not
    # attempt yet (e.g. no cross-entity theme/sector-level inference) --
    # never a fabricated capability, and never per-user data.
    architecture_notes: list[str] = Field(default_factory=list)
