from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

Domain = Literal["stocks", "sports", "poly", "social", "news", "crypto"]
EntityType = Literal["ticker", "team", "contract", "topic", "person"]


class DecisionTraceEntry(BaseModel):
    layer: str
    rule: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    timestamp: datetime


class ExecutionMetrics(BaseModel):
    schema_version: str = "1.0"
    layer: str
    pipeline_run_id: UUID
    event_id: Optional[UUID] = None
    latency_ms: int = Field(ge=0)
    success: bool
    warnings: list[str] = Field(default_factory=list)
    retries: int = 0
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recorded_at: datetime


class ExecutionTrace(BaseModel):
    schema_version: str = "1.0"
    pipeline_run_id: UUID
    event_id: Optional[UUID] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: Literal["running", "complete", "failed", "partial"] = "running"
    layers: list[ExecutionMetrics] = Field(default_factory=list)
    final_output: Optional[UUID] = None
    error: Optional[str] = None


class Entity(BaseModel):
    entity_id: str
    entity_type: EntityType
    display_name: str
    domain: Domain
    attributes: dict = Field(default_factory=dict)


class Delta(BaseModel):
    field: str
    prior_value: Optional[object] = None
    new_value: object
    unit: Optional[str] = None
    changed_at: datetime


class Reference(BaseModel):
    ref_type: Literal["signal", "event", "memory", "entity"]
    ref_id: UUID
    description: Optional[str] = None
