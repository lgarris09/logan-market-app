from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryWrite(BaseModel):
    schema_version: str = "1.0"
    write_id: UUID
    write_type: Literal["new_record", "update_record", "decay_update", "trust_update", "hypothesis_update"]
    target: Literal["memory", "user_model", "trust_registry", "mental_model"]
    content: object
    source_signal: Optional[UUID] = None
    confidence: float = Field(ge=0.0, le=1.0)
    authorized_at: datetime
