from app.celery_app import celery_app
from app.tasks.health import ping


def test_celery_uses_redis_url_from_settings():
    assert celery_app.conf.broker_url == "redis://localhost:6379/15"
    assert celery_app.conf.result_backend == "redis://localhost:6379/15"


def test_health_task_registered():
    assert ping.name == "app.tasks.health.ping"
    assert celery_app.tasks["app.tasks.health.ping"].run() == "pong"


def test_pilot_city_beat_schedule_is_configured():
    schedule = celery_app.conf.beat_schedule

    assert schedule["refresh-waterloo-places-daily"]["task"] == "app.tasks.ingestion.ingest_area"
    assert schedule["refresh-waterloo-places-daily"]["kwargs"]["city"] == "Waterloo"
    assert schedule["refresh-toronto-places-daily"]["task"] == "app.tasks.ingestion.ingest_area"
    assert schedule["refresh-toronto-places-daily"]["kwargs"]["city"] == "Toronto"
