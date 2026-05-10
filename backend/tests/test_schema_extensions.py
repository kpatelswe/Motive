from pathlib import Path

from app.models.base import HangoutStatus
from app.models.hangout import HangoutRequest
from app.models.place import Place


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "8c2d4b0e9a31_add_place_embeddings_and_coverage.py"
)


def test_place_has_pgvector_and_coverage_columns():
    assert Place.__table__.c.embedding.type.dim == 384
    assert "coverage_key" in Place.__table__.c
    assert "region" in Place.__table__.c
    assert "country" in Place.__table__.c


def test_hangout_request_has_geocoded_coverage_columns():
    assert "coverage_key" in HangoutRequest.__table__.c
    assert "resolved_city" in HangoutRequest.__table__.c
    assert "latitude" in HangoutRequest.__table__.c
    assert "longitude" in HangoutRequest.__table__.c


def test_hangout_status_supports_generation_states():
    assert HangoutStatus.COVERAGE_PENDING.value == "coverage_pending"
    assert HangoutStatus.GENERATING.value == "generating"


def test_migration_enables_vector_extension_and_index():
    migration = MIGRATION_PATH.read_text()

    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration
    assert "ix_places_embedding_hnsw" in migration
    assert "Vector(384)" in migration
