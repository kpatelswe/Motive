from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.models.base import PriceTier

GOOGLE_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.primaryType,"
    "places.types,"
    "places.location,"
    "places.rating,"
    "places.priceLevel,"
    "nextPageToken"
)

VIBE_KEYWORDS = {
    "chill": {
        "bakery",
        "book_store",
        "cafe",
        "coffee_shop",
        "library",
        "museum",
        "park",
        "restaurant",
    },
    "hype": {
        "amusement_center",
        "bar",
        "bowling_alley",
        "concert_hall",
        "night_club",
        "stadium",
    },
    "romantic": {
        "art_gallery",
        "bar",
        "fine_dining_restaurant",
        "movie_theater",
        "restaurant",
        "spa",
        "wine_bar",
    },
    "outdoorsy": {
        "beach",
        "campground",
        "hiking_area",
        "park",
        "tourist_attraction",
        "zoo",
    },
}

PRICE_LEVEL_MAP = {
    "PRICE_LEVEL_FREE": PriceTier.LOW,
    "PRICE_LEVEL_INEXPENSIVE": PriceTier.LOW,
    "PRICE_LEVEL_MODERATE": PriceTier.MED,
    "PRICE_LEVEL_EXPENSIVE": PriceTier.HIGH,
    "PRICE_LEVEL_VERY_EXPENSIVE": PriceTier.LUXURY,
}


@dataclass(frozen=True)
class GooglePlaceCandidate:
    google_place_id: str
    name: str
    address: str | None
    city: str
    region: str | None
    country: str | None
    coverage_key: str
    category: str | None
    price_tier: PriceTier | None
    vibe_tags: list[str]
    latitude: float | None
    longitude: float | None
    avg_external_rating: float | None


def normalize_coverage_key(city: str, region: str | None = None, country: str | None = None) -> str:
    parts = [city, region or "", country or ""]
    return ":".join(part.strip().lower().replace(" ", "-") for part in parts if part and part.strip())


def infer_vibe_tags(name: str, category: str | None, google_types: list[str]) -> list[str]:
    searchable = {item.lower() for item in google_types}
    if category:
        searchable.add(category.lower())
    searchable.update(name.lower().replace("-", " ").split())

    tags = [
        vibe
        for vibe, keywords in VIBE_KEYWORDS.items()
        if searchable.intersection(keywords)
    ]
    return tags or ["chill"]


def map_price_tier(price_level: str | None) -> PriceTier | None:
    if not price_level:
        return None
    return PRICE_LEVEL_MAP.get(price_level)


def _category_from_place(place: dict[str, Any]) -> str | None:
    category = place.get("primaryType")
    if not category:
        types = place.get("types") or []
        category = types[0] if types else None
    return category.replace("_", " ") if category else None


def parse_google_place(
    place: dict[str, Any],
    *,
    city: str,
    region: str | None,
    country: str | None,
) -> GooglePlaceCandidate:
    google_types = place.get("types") or []
    display_name = place.get("displayName") or {}
    location = place.get("location") or {}
    category = _category_from_place(place)
    name = display_name.get("text") or "Unnamed place"

    return GooglePlaceCandidate(
        google_place_id=place["id"],
        name=name,
        address=place.get("formattedAddress"),
        city=city,
        region=region,
        country=country,
        coverage_key=normalize_coverage_key(city, region, country),
        category=category,
        price_tier=map_price_tier(place.get("priceLevel")),
        vibe_tags=infer_vibe_tags(name, category, google_types),
        latitude=location.get("latitude"),
        longitude=location.get("longitude"),
        avg_external_rating=place.get("rating"),
    )


class GooglePlacesClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        text_search_url: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.api_key = api_key or settings.google_places_api_key
        self.text_search_url = text_search_url or settings.google_places_text_search_url
        self.timeout_seconds = timeout_seconds

    def search_city(
        self,
        *,
        city: str,
        region: str | None = None,
        country: str | None = None,
        query: str = "restaurants cafes parks activities",
        max_pages: int = 2,
        page_size: int = 20,
    ) -> list[GooglePlaceCandidate]:
        if not self.api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY is required for place ingestion")

        text_query = " ".join(part for part in [query, city, region, country] if part)
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": GOOGLE_FIELD_MASK,
        }
        candidates: list[GooglePlaceCandidate] = []
        page_token: str | None = None

        with httpx.Client(timeout=self.timeout_seconds) as client:
            for _ in range(max_pages):
                payload: dict[str, Any] = {
                    "textQuery": text_query,
                    "pageSize": page_size,
                }
                if page_token:
                    payload["pageToken"] = page_token

                response = client.post(self.text_search_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                candidates.extend(
                    parse_google_place(place, city=city, region=region, country=country)
                    for place in data.get("places", [])
                    if place.get("id")
                )

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return candidates
