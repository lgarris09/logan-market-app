from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

InteractionType = Literal["view", "click", "dismiss", "save", "act", "share"]
InferredIntent = Literal[
    "interested", "curious", "dismissing", "confused", "accidental", "researching", "unknown"
]


class FeedbackSignal(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    interaction_type: InteractionType
    inferred_intent: InferredIntent
    intent_confidence: float = Field(ge=0.0, le=1.0)
    duration_ms: Optional[int] = None
    raw_interaction: str
    observed_at: datetime
    decision_trace: list = Field(default_factory=list)

    @model_validator(mode="after")
    def _low_confidence_is_unknown(self):
        if self.intent_confidence < 0.50 and self.inferred_intent != "unknown":
            raise ValueError("inferred_intent must be 'unknown' when intent_confidence < 0.50")
        return self


class OutcomeRecord(BaseModel):
    schema_version: str = "1.0"
    outcome_id: UUID
    event_id: UUID
    outcome_type: Literal[
        "signal_accuracy", "source_reliability", "user_value", "market_resolution", "event_resolution"
    ]
    result: object
    expected: Optional[object] = None
    accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    resolved_at: datetime
    delay_window: Literal["immediate", "hours", "days", "months"]
    learning_applied: bool = False
