from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlanRatingCreate(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = None
    would_repeat: bool | None = None


class PlanRatingOut(BaseModel):
    id: UUID
    plan_id: UUID
    score: int
    comment: str | None
    would_repeat: bool | None
    created_at: datetime

    model_config = {"from_attributes": True}
