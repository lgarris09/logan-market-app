from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import Domain, EntityType


class RawSignal(BaseModel):
    schema_version: str = "1.0"
    domain: Domain
    source_id: str
    source_name: str
    raw_value: object
    captured_at: datetime
    metadata: dict = Field(default_factory=dict)
    # Intentionally left empty by every V1 receptor (V3.1.4 BATCH-2 review):
    # a receptor captures a signal, it doesn't decide anything about it --
    # there is no deterministic rule to trace at this layer. Reserved for a
    # receptor implementation that does make a capture-time decision (e.g.
    # filtering, dedup against a live feed) once live receptors exist.
    decision_trace: list = Field(default_factory=list)


class NormalizedSignal(BaseModel):
    schema_version: str = "1.0"
    signal_id: UUID
    domain: Domain
    entity_id: str
    entity_type: EntityType
    signal_type: str
    value: object
    unit: Optional[str] = None
    source_id: str
    source_name: str
    captured_at: datetime
    normalized_at: datetime
    decision_trace: list = Field(default_factory=list)
