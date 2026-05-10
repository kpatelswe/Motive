from app.models.base import PriceTier
from app.services.embeddings import EMBEDDING_DIMENSIONS, deterministic_embedding, place_embedding_text
from app.services.google_places import (
    infer_vibe_tags,
    map_price_tier,
    normalize_coverage_key,
    parse_google_place,
)


def test_normalize_coverage_key_is_stable():
    assert normalize_coverage_key(" Waterloo ", "ON", "CA") == "waterloo:on:ca"


def test_google_place_parser_maps_core_fields():
    place = {
        "id": "places/google-1",
        "displayName": {"text": "Kitchener Market"},
        "formattedAddress": "300 King St E, Kitchener, ON",
        "primaryType": "restaurant",
        "types": ["restaurant", "food"],
        "location": {"latitude": 43.4516, "longitude": -80.4925},
        "rating": 4.6,
        "priceLevel": "PRICE_LEVEL_MODERATE",
    }

    candidate = parse_google_place(place, city="Waterloo", region="ON", country="CA")

    assert candidate.google_place_id == "places/google-1"
    assert candidate.coverage_key == "waterloo:on:ca"
    assert candidate.price_tier == PriceTier.MED
    assert candidate.category == "restaurant"
    assert candidate.avg_external_rating == 4.6


def test_vibe_and_price_mapping_are_deterministic():
    assert infer_vibe_tags("Trail Cafe", "park", ["hiking_area"]) == ["chill", "outdoorsy"]
    assert map_price_tier("PRICE_LEVEL_VERY_EXPENSIVE") == PriceTier.LUXURY


def test_deterministic_embedding_has_expected_dimension_and_norm():
    text = place_embedding_text(
        name="Cafe 22",
        city="Waterloo",
        category="cafe",
        vibe_tags=["chill"],
        price_tier="low",
    )
    embedding = deterministic_embedding(text)

    assert len(embedding) == EMBEDDING_DIMENSIONS
    assert embedding == deterministic_embedding(text)
    assert abs(sum(value * value for value in embedding) - 1.0) < 0.000001
