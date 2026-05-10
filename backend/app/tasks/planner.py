from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.base import HangoutStatus
from app.models.hangout import HangoutRequest
from app.services.planner import (
    assemble_plan_groups,
    enqueue_coverage_ingestion,
    has_coverage,
    persist_plan_groups,
    resolve_location_text,
    retrieve_scored_places,
)


@celery_app.task(name="app.tasks.planner.generate_plans")
def generate_plans_task(request_id: str) -> dict[str, str | int]:
    db = SessionLocal()
    try:
        request = db.get(HangoutRequest, UUID(request_id))
        if request is None:
            raise ValueError(f"Hangout request {request_id} not found")

        location = resolve_location_text(request.location_text)
        request.resolved_city = location.city
        request.resolved_region = location.region
        request.resolved_country = location.country
        request.coverage_key = location.coverage_key
        request.latitude = location.latitude
        request.longitude = location.longitude

        if not has_coverage(db, location.coverage_key):
            job = enqueue_coverage_ingestion(db, location)
            request.status = HangoutStatus.COVERAGE_PENDING
            db.commit()
            return {
                "status": request.status.value,
                "coverage_key": location.coverage_key,
                "coverage_job_id": str(job.id),
            }

        request.status = HangoutStatus.GENERATING
        db.commit()

        scored_places = retrieve_scored_places(db, request, location)
        plan_groups = assemble_plan_groups(scored_places, request.duration_minutes)
        if len(plan_groups) < 3:
            job = enqueue_coverage_ingestion(db, location)
            request.status = HangoutStatus.COVERAGE_PENDING
            db.commit()
            return {
                "status": request.status.value,
                "coverage_key": location.coverage_key,
                "coverage_job_id": str(job.id),
            }

        persist_plan_groups(db, request, plan_groups)
        request.status = HangoutStatus.GENERATED
        db.commit()
        return {
            "status": request.status.value,
            "coverage_key": location.coverage_key,
            "plans": len(plan_groups),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
