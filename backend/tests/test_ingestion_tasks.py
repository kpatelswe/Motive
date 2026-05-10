from app.celery_app import celery_app
from app.models.base import CoverageJobStatus, PlaceSource
from app.services.google_places import GooglePlaceCandidate
from app.tasks.ingestion import upsert_place


class _FakeQuery:
    def filter(self, *_args):
        return self

    def one_or_none(self):
        return None


class _FakeSession:
    def __init__(self):
        self.added = []

    def query(self, _model):
        return _FakeQuery()

    def add(self, item):
        self.added.append(item)


def test_ingest_area_task_is_registered():
    assert "app.tasks.ingestion.ingest_area" in celery_app.tasks


def test_coverage_job_status_values():
    assert CoverageJobStatus.PENDING.value == "pending"
    assert CoverageJobStatus.RUNNING.value == "running"
    assert CoverageJobStatus.COMPLETED.value == "completed"
    assert CoverageJobStatus.FAILED.value == "failed"


def test_upsert_place_maps_candidate_to_scraped_place():
    db = _FakeSession()
    candidate = GooglePlaceCandidate(
        google_place_id="places/google-1",
        name="Abe Erb Waterloo",
        address="15 King St S, Waterloo, ON",
        city="Waterloo",
        region="ON",
        country="CA",
        coverage_key="waterloo:on:ca",
        category="bar",
        price_tier=None,
        vibe_tags=["hype"],
        latitude=43.465,
        longitude=-80.522,
        avg_external_rating=4.4,
    )

    place = upsert_place(db, candidate)

    assert db.added == [place]
    assert place.google_place_id == "places/google-1"
    assert place.source == PlaceSource.SCRAPED
    assert place.coverage_key == "waterloo:on:ca"
    assert len(place.embedding) == 384
