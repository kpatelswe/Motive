from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, PriceTier, PlaceSource, UUIDMixin, TimestampMixin


class Place(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "places"

    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    city = Column(String, nullable=False, index=True)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    coverage_key = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True)
    price_tier = Column(Enum(PriceTier), nullable=True)
    vibe_tags = Column(ARRAY(String), nullable=False, default=list)
    google_place_id = Column(String, unique=True, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    avg_external_rating = Column(Float, nullable=True)
    embedding = Column(Vector(384), nullable=True)
    source = Column(Enum(PlaceSource), nullable=False, default=PlaceSource.MANUAL)
    is_active = Column(Boolean, nullable=False, default=True)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)

    stops = relationship("PlanStop", back_populates="place")
