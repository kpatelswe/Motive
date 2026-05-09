from sqlalchemy import Boolean, Column, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class PlanRating(UUIDMixin, Base):
    __tablename__ = "plan_ratings"

    plan_id = Column(UUID(as_uuid=True), ForeignKey("generated_plans.id"), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    would_repeat = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    plan = relationship("GeneratedPlan", back_populates="rating")
    user = relationship("User", back_populates="ratings")
