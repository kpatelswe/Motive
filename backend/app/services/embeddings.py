import hashlib
import math

EMBEDDING_DIMENSIONS = 384


def deterministic_embedding(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    values: list[float] = []
    seed = text.strip().lower().encode("utf-8")

    for index in range(dimensions):
        digest = hashlib.sha256(seed + index.to_bytes(2, "big")).digest()
        integer = int.from_bytes(digest[:4], "big")
        values.append((integer / 2**32) * 2 - 1)

    magnitude = math.sqrt(sum(value * value for value in values))
    if not magnitude:
        return [0.0] * dimensions
    return [value / magnitude for value in values]


def place_embedding_text(
    *,
    name: str,
    city: str,
    category: str | None,
    vibe_tags: list[str],
    price_tier: str | None,
) -> str:
    return " | ".join(
        part
        for part in [
            name,
            category or "",
            city,
            price_tier or "",
            " ".join(sorted(vibe_tags)),
        ]
        if part
    )
