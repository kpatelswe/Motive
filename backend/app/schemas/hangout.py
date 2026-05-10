from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.base import HangoutStatus, PriceTier, Vibe
from app.schemas.place import PlaceOut

class HangoutRequestCreate(BaseModel):
    location_text: str
    vibe: Vibe
    price_tier: PriceTier
    duration_minutes: int = Field(gt=0)
    preferred_datetime: datetime | None = None
    group_size: int | None = Field(default=None, gt=0)

class HangoutRequestOut(BaseModel):
    id: UUID
    location_text: str
    resolved_city: str | None = None
    resolved_region: str | None = None
    resolved_country: str | None = None
    coverage_key: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    vibe: Vibe
    price_tier: PriceTier
    duration_minutes: int
    preferred_datetime: datetime | None
    group_size: int | None
    status: HangoutStatus
    created_at: datetime

    model_config = {"from_attributes": True}

class PlanStopOut(BaseModel):
    stop_order: int
    duration_minutes: int | None
    notes: str | None
    place: PlaceOut

    model_config = {"from_attributes": True}

class GeneratedPlanOut(BaseModel):
    id: UUID
    plan_number: int
    title: str
    description: str
    estimated_cost_cents: int | None
    estimated_duration_minutes: int | None
    is_selected: bool
    stops: list[PlanStopOut]

    model_config = {"from_attributes": True}

class HangoutRequestWithPlansOut(HangoutRequestOut):
    plans: list[GeneratedPlanOut]

class PlanSelectionRequest(BaseModel):
    plan_id: UUID

class HangoutRequestStatusOut(BaseModel):
    request: HangoutRequestWithPlansOut
    message: str | None = None
    coverage_job_id: UUID | None = None
