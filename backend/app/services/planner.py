from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.base import CoverageJobStatus, HangoutStatus, PriceTier, Vibe
from app.models.coverage import CoverageJob
from app.models.hangout import GeneratedPlan, HangoutRequest, PlanStop
from app.models.place import Place
from app.services.embeddings import deterministic_embedding
from app.services.google_places import normalize_coverage_key
from app.tasks.ingestion import ingest_area


@dataclass(frozen=True)
class ResolvedLocation:
    city: str
    region: str | None
    country: str | None
    coverage_key: str
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class ScoredPlace:
    place: Place
    score: float


PRICE_ORDER = {
    PriceTier.LOW: 0,
    PriceTier.MED: 1,
    PriceTier.HIGH: 2,
    PriceTier.LUXURY: 3,
}

PILOT_LOCATIONS = {
    "waterloo": ResolvedLocation("Waterloo", "ON", "CA", "waterloo:on:ca", 43.4643, -80.5204),
    "toronto": ResolvedLocation("Toronto", "ON", "CA", "toronto:on:ca", 43.6532, -79.3832),
}


def resolve_location_text(location_text: str) -> ResolvedLocation:
    normalized = location_text.strip().lower()
    for key, location in PILOT_LOCATIONS.items():
        if key in normalized:
            return location

    parts = [part.strip() for part in location_text.split(",") if part.strip()]
    city = parts[0] if parts else location_text.strip()
    region = parts[1] if len(parts) > 1 else None
    country = parts[2] if len(parts) > 2 else "CA"
    return ResolvedLocation(
        city=city,
        region=region,
        country=country,
        coverage_key=normalize_coverage_key(city, region, country),
    )


def has_coverage(db: Session, coverage_key: str, *, min_places: int | None = None) -> bool:
    threshold = min_places if min_places is not None else settings.coverage_min_places
    active_places = (
        db.query(func.count(Place.id))
        .filter(Place.coverage_key == coverage_key, Place.is_active.is_(True))
        .scalar()
    )
    return (active_places or 0) >= threshold


def enqueue_coverage_ingestion(db: Session, location: ResolvedLocation) -> CoverageJob:
    job = db.query(CoverageJob).filter(CoverageJob.coverage_key == location.coverage_key).one_or_none()
    if job and job.status in {CoverageJobStatus.PENDING, CoverageJobStatus.RUNNING}:
        return job

    if job is None:
        job = CoverageJob(
            coverage_key=location.coverage_key,
            city=location.city,
            region=location.region,
            country=location.country,
        )
        db.add(job)

    job.status = CoverageJobStatus.PENDING
    job.message = "Queued Google Places ingestion"
    result = ingest_area.apply_async(
        kwargs={
            "city": location.city,
            "region": location.region,
            "country": location.country,
        }
    )
    job.celery_task_id = result.id
    return job


def request_query_text(request: HangoutRequest, location: ResolvedLocation) -> str:
    return " ".join(
        [
            request.vibe.value,
            request.price_tier.value,
            str(request.duration_minutes),
            "minutes",
            location.city,
            location.region or "",
            location.country or "",
        ]
    ).strip()


def _haversine_km(
    lat1: float | None,
    lon1: float | None,
    lat2: float | None,
    lon2: float | None,
) -> float | None:
    if None in {lat1, lon1, lat2, lon2}:
        return None
    radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * radius_km * asin(sqrt(a))


def _price_match(requested: PriceTier, actual: PriceTier | None) -> float:
    if actual is None:
        return 0.4
    distance = abs(PRICE_ORDER[requested] - PRICE_ORDER[actual])
    return max(0.0, 1.0 - (distance * 0.35))


def _cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def score_place(place: Place, request: HangoutRequest, location: ResolvedLocation) -> float:
    distance = _haversine_km(location.latitude, location.longitude, place.latitude, place.longitude)
    distance_score = 0.5 if distance is None else max(0.0, 1.0 - min(distance, 25.0) / 25.0)
    vibe_score = 1.0 if request.vibe.value in (place.vibe_tags or []) else 0.25
    rating_score = (place.avg_external_rating or 0.0) / 5.0
    vector_score = _cosine_similarity(
        place.embedding,
        deterministic_embedding(request_query_text(request, location)),
    )

    return (
        0.25 * distance_score
        + 0.25 * _price_match(request.price_tier, place.price_tier)
        + 0.25 * vibe_score
        + 0.15 * rating_score
        + 0.10 * max(0.0, vector_score)
    )


def retrieve_scored_places(
    db: Session,
    request: HangoutRequest,
    location: ResolvedLocation,
    *,
    limit: int = 50,
) -> list[ScoredPlace]:
    candidates = (
        db.query(Place)
        .filter(
            Place.coverage_key == location.coverage_key,
            Place.is_active.is_(True),
        )
        .limit(limit)
        .all()
    )
    scored = [ScoredPlace(place=place, score=score_place(place, request, location)) for place in candidates]
    return sorted(scored, key=lambda item: item.score, reverse=True)


def assemble_plan_groups(scored_places: list[ScoredPlace], duration_minutes: int) -> list[list[ScoredPlace]]:
    groups: list[list[ScoredPlace]] = []
    used_ids: set[UUID] = set()
    max_stops = 2 if duration_minutes >= 120 else 1

    for scored in scored_places:
        if len(groups) == 3:
            break
        if scored.place.id in used_ids:
            continue

        group = [scored]
        used_ids.add(scored.place.id)

        if max_stops > 1:
            partner = next(
                (
                    candidate
                    for candidate in scored_places
                    if candidate.place.id not in used_ids
                    and candidate.place.category != scored.place.category
                ),
                None,
            )
            if partner:
                group.append(partner)
                used_ids.add(partner.place.id)

        groups.append(group)

    return groups


def persist_plan_groups(
    db: Session,
    request: HangoutRequest,
    plan_groups: list[list[ScoredPlace]],
) -> None:
    request.plans.clear()
    for plan_index, group in enumerate(plan_groups, start=1):
        names = [scored.place.name for scored in group]
        plan = GeneratedPlan(
            request=request,
            plan_number=plan_index,
            title=f"Plan {plan_index}: {names[0]}",
            description=" then ".join(names),
            estimated_duration_minutes=request.duration_minutes,
        )
        db.add(plan)
        stop_minutes = max(30, request.duration_minutes // max(len(group), 1))
        for stop_index, scored in enumerate(group, start=1):
            db.add(
                PlanStop(
                    plan=plan,
                    place=scored.place,
                    stop_order=stop_index,
                    duration_minutes=stop_minutes,
                    notes=f"Score: {scored.score:.2f}",
                )
            )
