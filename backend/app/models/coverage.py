from sqlalchemy import Column, DateTime, Enum, String, Text
from sqlalchemy.sql import func

from app.models.base import Base, CoverageJobStatus, TimestampMixin, UUIDMixin


class CoverageJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "coverage_jobs"

    coverage_key = Column(String, unique=True, nullable=False, index=True)
    city = Column(String, nullable=False)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    status = Column(Enum(CoverageJobStatus), nullable=False, default=CoverageJobStatus.PENDING)
    celery_task_id = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
