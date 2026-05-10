from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.base import CoverageJobStatus, PlaceSource
from app.models.coverage import CoverageJob
from app.models.place import Place
from app.services.embeddings import deterministic_embedding, place_embedding_text
from app.services.google_places import (
    GooglePlaceCandidate,
    GooglePlacesClient,
    normalize_coverage_key,
)


def upsert_place(db: Session, candidate: GooglePlaceCandidate) -> Place:
    place = (
        db.query(Place)
        .filter(Place.google_place_id == candidate.google_place_id)
        .one_or_none()
    )
    if place is None:
        place = Place(google_place_id=candidate.google_place_id)
        db.add(place)

    place.name = candidate.name
    place.address = candidate.address
    place.city = candidate.city
    place.region = candidate.region
    place.country = candidate.country
    place.coverage_key = candidate.coverage_key
    place.category = candidate.category
    place.price_tier = candidate.price_tier
    place.vibe_tags = candidate.vibe_tags
    place.latitude = candidate.latitude
    place.longitude = candidate.longitude
    place.avg_external_rating = candidate.avg_external_rating
    place.source = PlaceSource.SCRAPED
    place.is_active = True
    place.last_scraped_at = datetime.now(timezone.utc)
    place.embedding = deterministic_embedding(
        place_embedding_text(
            name=place.name,
            city=place.city,
            category=place.category,
            vibe_tags=place.vibe_tags,
            price_tier=place.price_tier.value if place.price_tier else None,
        )
    )
    return place


def _get_or_create_coverage_job(
    db: Session,
    *,
    city: str,
    region: str | None,
    country: str | None,
) -> CoverageJob:
    coverage_key = normalize_coverage_key(city, region, country)
    job = db.query(CoverageJob).filter(CoverageJob.coverage_key == coverage_key).one_or_none()
    if job:
        job.last_requested_at = datetime.now(timezone.utc)
        return job

    job = CoverageJob(
        coverage_key=coverage_key,
        city=city,
        region=region,
        country=country,
        status=CoverageJobStatus.PENDING,
    )
    db.add(job)
    return job


@celery_app.task(name="app.tasks.ingestion.ingest_area")
def ingest_area(
    *,
    city: str,
    region: str | None = None,
    country: str | None = None,
    query: str = "restaurants cafes parks activities",
) -> dict[str, int | str]:
    db = SessionLocal()
    coverage_key = normalize_coverage_key(city, region, country)
    try:
        job = _get_or_create_coverage_job(db, city=city, region=region, country=country)
        job.status = CoverageJobStatus.RUNNING
        job.message = "Ingestion started"
        db.commit()

        candidates = GooglePlacesClient().search_city(
            city=city,
            region=region,
            country=country,
            query=query,
        )
        for candidate in candidates:
            upsert_place(db, candidate)

        job.status = CoverageJobStatus.COMPLETED
        job.message = f"Ingested {len(candidates)} places"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"coverage_key": coverage_key, "places": len(candidates)}
    except Exception as exc:
        db.rollback()
        job = _get_or_create_coverage_job(db, city=city, region=region, country=country)
        job.status = CoverageJobStatus.FAILED
        job.message = str(exc)
        db.commit()
        raise
    finally:
        db.close()
