from typing import Literal

from pydantic import BaseModel, Field

OpportunityCategory = Literal["stocks", "sports", "polymarket"]


class Opportunity(BaseModel):
    id: str
    category: OpportunityCategory
    title: str
    summary: str
    why_it_matters: str
    score: int = Field(ge=0, le=100)
    urgency: Literal["watch", "important", "now"]
    change_label: str
    source_label: str


class BriefingResponse(BaseModel):
    greeting: str
    headline: str
    opportunities: list[Opportunity]


class AskRequest(BaseModel):
    message: str


class AskResponse(BaseModel):
    answer: str
