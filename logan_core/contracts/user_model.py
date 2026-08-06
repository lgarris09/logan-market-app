from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import Domain


class Interest(BaseModel):
    domain: Domain
    topic: str
    weight: float = Field(ge=0.0, le=1.0)
    source: Literal["explicit", "inferred"]
    created_at: datetime
    last_updated: datetime


class Holding(BaseModel):
    domain: Domain
    entity_id: str
    display_name: str
    size: Optional[object] = None
    added_at: datetime


class Expertise(BaseModel):
    domain: Domain
    level: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    last_updated: datetime


class DomainPref(BaseModel):
    domain: Domain
    active: bool
    weight: float = Field(ge=0.0, le=1.0)
    last_updated: datetime


class BehaviorPattern(BaseModel):
    label: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)


class UserModel(BaseModel):
    schema_version: str = "1.0"
    user_id: str
    interests: list[Interest] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    holdings: list[Holding] = Field(default_factory=list)
    risk_tolerance: Literal["conservative", "moderate", "aggressive", "unknown"] = (
        "unknown"
    )
    inferred_expertise: list[Expertise] = Field(default_factory=list)
    domain_preferences: list[DomainPref] = Field(default_factory=list)
    established_behaviors: list[BehaviorPattern] = Field(default_factory=list)
    model_confidence: float = Field(ge=0.0, le=1.0)
    last_updated: datetime
    version: int = Field(ge=1, default=1)
