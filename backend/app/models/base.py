from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Vibe(str, Enum):
    CHILL = "chill"
    HYPE = "hype"
    ROMANTIC = "romantic"
    OUTDOORSY = "outdoorsy"


class PriceTier(str, Enum):
    LOW = "low"       # $
    MED = "med"       # $$
    HIGH = "high"     # $$$
    LUXURY = "luxury" # $$$$


class HangoutStatus(str, Enum):
    PENDING = "pending"
    GENERATED = "generated"
    SELECTED = "selected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlaceSource(str, Enum):
    MANUAL = "manual"
    SCRAPED = "scraped"


class UUIDMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
