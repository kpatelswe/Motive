from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    google_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)

    hangout_requests = relationship("HangoutRequest", back_populates="user")
    ratings = relationship("PlanRating", back_populates="user")
