from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base, HangoutStatus, PriceTier, UUIDMixin, TimestampMixin, Vibe


class HangoutRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "hangout_requests"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    location_text = Column(String, nullable=False)
    vibe = Column(Enum(Vibe), nullable=False)
    price_tier = Column(Enum(PriceTier), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    preferred_datetime = Column(DateTime(timezone=True), nullable=True)
    group_size = Column(Integer, nullable=True)
    status = Column(Enum(HangoutStatus), nullable=False, default=HangoutStatus.PENDING)

    user = relationship("User", back_populates="hangout_requests")
    plans = relationship("GeneratedPlan", back_populates="request", cascade="all, delete-orphan")


class GeneratedPlan(UUIDMixin, Base):
    __tablename__ = "generated_plans"

    request_id = Column(UUID(as_uuid=True), ForeignKey("hangout_requests.id"), nullable=False)
    plan_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    estimated_cost_cents = Column(Integer, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    is_selected = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("HangoutRequest", back_populates="plans")
    stops = relationship(
        "PlanStop",
        back_populates="plan",
        order_by="PlanStop.stop_order",
        cascade="all, delete-orphan",
    )
    rating = relationship("PlanRating", back_populates="plan", uselist=False)


class PlanStop(UUIDMixin, Base):
    __tablename__ = "plan_stops"

    plan_id = Column(UUID(as_uuid=True), ForeignKey("generated_plans.id"), nullable=False)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"), nullable=False)
    stop_order = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

    plan = relationship("GeneratedPlan", back_populates="stops")
    place = relationship("Place", back_populates="stops")
