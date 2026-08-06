from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PolicyResult(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    permitted: bool
    communication_mode: Literal["analysis", "alert", "informational", "suppressed"]
    language_constraints: list[str] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    policy_rules_applied: list[str] = Field(default_factory=list)
    evaluated_at: datetime
    decision_trace: list = Field(default_factory=list)

    @model_validator(mode="after")
    def _suppressed_when_not_permitted(self):
        if not self.permitted and self.communication_mode != "suppressed":
            raise ValueError(
                "communication_mode must be 'suppressed' when permitted is False"
            )
        return self
