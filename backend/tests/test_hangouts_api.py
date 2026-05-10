from datetime import datetime, timezone
from uuid import uuid4

from app.main import app
from app.models.base import HangoutStatus, PriceTier, Vibe
from app.models.coverage import CoverageJob
from app.models.hangout import HangoutRequest
from app.routers.hangouts import _status_response


class _FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def one_or_none(self):
        return self.result


class _FakeDb:
    def __init__(self, result):
        self.result = result

    def query(self, _model):
        return _FakeQuery(self.result)


def test_hangout_routes_are_registered():
    paths = {route.path for route in app.routes}

    assert "/hangouts" in paths
    assert "/hangouts/{request_id}" in paths
    assert "/hangouts/{request_id}/select" in paths
    assert "/hangouts/{request_id}/rating" in paths


def test_status_response_includes_cold_start_message_and_job_id():
    coverage_job = CoverageJob(
        id=uuid4(),
        coverage_key="waterloo:on:ca",
        city="Waterloo",
        region="ON",
        country="CA",
    )
    request = HangoutRequest(
        id=uuid4(),
        user_id=uuid4(),
        location_text="Waterloo",
        coverage_key="waterloo:on:ca",
        vibe=Vibe.CHILL,
        price_tier=PriceTier.MED,
        duration_minutes=90,
        status=HangoutStatus.COVERAGE_PENDING,
        created_at=datetime.now(timezone.utc),
    )
    request.plans = []

    response = _status_response(_FakeDb(coverage_job), request)

    assert response.coverage_job_id == coverage_job.id
    assert response.message == "We're gathering spots in your area. Check back in a few minutes."
    assert response.request.status == HangoutStatus.COVERAGE_PENDING
