from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import Domain


class MentalModel(BaseModel):
    schema_version: str = "1.0"
    model_id: UUID
    domain: Domain
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting: list[str] = Field(default_factory=list)
    opposing: list[str] = Field(default_factory=list)
    trend: Literal["strengthening", "weakening", "stable", "new", "retired"]
    created_at: datetime
    last_updated: datetime
    retired_at: Optional[datetime] = None
    decision_trace: list = Field(default_factory=list)


# RESERVED, UNWIRED (V3.1.4 BATCH-2 review): MentalModelEngine.process()
# returns a plain MentalModel, never a MentalModelDelta -- nothing in
# logan_core constructs this class. Per ADR-015, Mental Model is V1 pass-
# through/data-collection only; MentalModelDelta (with its trigger_event_id
# field pointing at a TriggerEvent contract that also doesn't exist in code
# yet) belongs to the V2 activation path this project has deliberately not
# built. Not required by the current vertical slice; kept, not removed, since
# ADR-015 explicitly anticipates "V1->V2 activation later requires no new
# pipeline stage" -- this is the typed shape that later work fills in.
class MentalModelDelta(BaseModel):
    schema_version: str = "2.0"
    model_id: UUID
    prior_confidence: float = Field(ge=0.0, le=1.0)
    new_confidence: float = Field(ge=0.0, le=1.0)
    delta: float
    trigger_event_id: UUID
    delta_is_signal: bool
    delta_threshold: float = 0.10
    computed_at: datetime
