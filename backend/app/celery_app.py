from celery import Celery

from app.config import settings

celery_app = Celery(
    "motive",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.health",
        "app.tasks.ingestion",
        "app.tasks.planner",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Toronto",
    enable_utc=True,
    beat_schedule={
        "refresh-waterloo-places-daily": {
            "task": "app.tasks.ingestion.ingest_area",
            "schedule": 60 * 60 * 24,
            "kwargs": {"city": "Waterloo", "region": "ON", "country": "CA"},
        },
        "refresh-toronto-places-daily": {
            "task": "app.tasks.ingestion.ingest_area",
            "schedule": 60 * 60 * 24,
            "kwargs": {"city": "Toronto", "region": "ON", "country": "CA"},
        },
    },
)
