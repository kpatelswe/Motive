from uuid import uuid4

from app.celery_app import celery_app
from app.models.base import PriceTier, Vibe
from app.models.hangout import HangoutRequest
from app.models.place import Place
from app.services.embeddings import deterministic_embedding
from app.services.planner import (
    ScoredPlace,
    assemble_plan_groups,
    resolve_location_text,
    score_place,
)
from app.tasks.planner import generate_plans_task


def _request() -> HangoutRequest:
    return HangoutRequest(
        user_id=uuid4(),
        location_text="Waterloo, ON",
        vibe=Vibe.CHILL,
        price_tier=PriceTier.MED,
        duration_minutes=90,
    )


def _place(
    name: str,
    *,
    category: str = "cafe",
    vibe_tags: list[str] | None = None,
    rating: float = 4.5,
) -> Place:
    place = Place(
        name=name,
        city="Waterloo",
        region="ON",
        country="CA",
        coverage_key="waterloo:on:ca",
        category=category,
        price_tier=PriceTier.MED,
        vibe_tags=vibe_tags or ["chill"],
        latitude=43.464,
        longitude=-80.52,
        avg_external_rating=rating,
        embedding=deterministic_embedding(name),
    )
    place.id = uuid4()
    return place


def test_generate_plans_task_is_registered():
    assert generate_plans_task.name == "app.tasks.planner.generate_plans"
    assert "app.tasks.planner.generate_plans" in celery_app.tasks


def test_resolve_location_prefers_pilot_city_registry():
    location = resolve_location_text("near University of Waterloo")

    assert location.city == "Waterloo"
    assert location.region == "ON"
    assert location.coverage_key == "waterloo:on:ca"
    assert location.latitude is not None


def test_score_place_prefers_matching_vibe_and_price():
    request = _request()
    location = resolve_location_text(request.location_text)
    matching = _place("Good Chill Cafe", vibe_tags=["chill"], rating=4.8)
    mismatch = _place("Loud Club", category="night club", vibe_tags=["hype"], rating=4.8)

    assert score_place(matching, request, location) > score_place(mismatch, request, location)


def test_assemble_plan_groups_returns_three_distinct_short_plans():
    scored_places = [
        ScoredPlace(place=_place(f"Place {index}"), score=1.0 - index * 0.1)
        for index in range(4)
    ]

    groups = assemble_plan_groups(scored_places, duration_minutes=90)

    assert len(groups) == 3
    assert all(len(group) == 1 for group in groups)
    assert len({group[0].place.id for group in groups}) == 3


def test_assemble_plan_groups_pairs_longer_plans_by_category():
    scored_places = [
        ScoredPlace(place=_place("Cafe", category="cafe"), score=1.0),
        ScoredPlace(place=_place("Park", category="park"), score=0.9),
        ScoredPlace(place=_place("Gallery", category="gallery"), score=0.8),
        ScoredPlace(place=_place("Bar", category="bar"), score=0.7),
        ScoredPlace(place=_place("Museum", category="museum"), score=0.6),
        ScoredPlace(place=_place("Bakery", category="bakery"), score=0.5),
    ]

    groups = assemble_plan_groups(scored_places, duration_minutes=150)

    assert len(groups) == 3
    assert all(len(group) == 2 for group in groups)
