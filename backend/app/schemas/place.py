from uuid import UUID

from pydantic import BaseModel

from app.models.base import PriceTier


class PlaceOut(BaseModel):
    id: UUID
    name: str
    address: str | None
    city: str
    category: str | None
    price_tier: PriceTier | None
    vibe_tags: list[str]
    avg_external_rating: float | None

    model_config = {"from_attributes": True}
