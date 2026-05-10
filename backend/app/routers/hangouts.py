from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.base import HangoutStatus
from app.models.coverage import CoverageJob
from app.models.hangout import GeneratedPlan, HangoutRequest, PlanStop
from app.models.rating import PlanRating
from app.models.user import User
from app.schemas.hangout import (
    HangoutRequestCreate,
    HangoutRequestStatusOut,
    HangoutRequestWithPlansOut,
    PlanSelectionRequest,
)
from app.schemas.rating import PlanRatingCreate, PlanRatingOut
from app.tasks.planner import generate_plans_task

router = APIRouter(prefix="/hangouts", tags=["hangouts"])


def _request_query(db: Session):
    return db.query(HangoutRequest).options(
        selectinload(HangoutRequest.plans)
        .selectinload(GeneratedPlan.stops)
        .selectinload(PlanStop.place)
    )


def _get_owned_request(db: Session, request_id: UUID, user: User) -> HangoutRequest:
    request = (
        _request_query(db)
        .filter(HangoutRequest.id == request_id, HangoutRequest.user_id == user.id)
        .one_or_none()
    )
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hangout request not found")
    return request


def _status_response(db: Session, request: HangoutRequest) -> HangoutRequestStatusOut:
    message = None
    coverage_job_id = None
    if request.status == HangoutStatus.COVERAGE_PENDING:
        message = "We're gathering spots in your area. Check back in a few minutes."
        if request.coverage_key:
            job = db.query(CoverageJob).filter(CoverageJob.coverage_key == request.coverage_key).one_or_none()
            coverage_job_id = job.id if job else None
    elif request.status == HangoutStatus.PENDING:
        message = "We're starting your plan generation."
    elif request.status == HangoutStatus.GENERATING:
        message = "We're building your plan options."

    return HangoutRequestStatusOut(
        request=HangoutRequestWithPlansOut.model_validate(request),
        message=message,
        coverage_job_id=coverage_job_id,
    )


@router.post("", response_model=HangoutRequestStatusOut, status_code=status.HTTP_202_ACCEPTED)
def create_hangout_request(
    body: HangoutRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = HangoutRequest(
        user_id=current_user.id,
        location_text=body.location_text,
        vibe=body.vibe,
        price_tier=body.price_tier,
        duration_minutes=body.duration_minutes,
        preferred_datetime=body.preferred_datetime,
        group_size=body.group_size,
        status=HangoutStatus.PENDING,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    generate_plans_task.delay(str(request.id))
    return _status_response(db, request)


@router.get("/{request_id}", response_model=HangoutRequestStatusOut)
def get_hangout_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = _get_owned_request(db, request_id, current_user)
    return _status_response(db, request)


@router.post("/{request_id}/select", response_model=HangoutRequestStatusOut)
def select_plan(
    request_id: UUID,
    body: PlanSelectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = _get_owned_request(db, request_id, current_user)
    selected_plan = next((plan for plan in request.plans if plan.id == body.plan_id), None)
    if selected_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    for plan in request.plans:
        plan.is_selected = plan.id == body.plan_id
    request.status = HangoutStatus.SELECTED
    db.commit()
    db.refresh(request)
    return _status_response(db, request)


@router.post("/{request_id}/rating", response_model=PlanRatingOut, status_code=status.HTTP_201_CREATED)
def rate_selected_plan(
    request_id: UUID,
    body: PlanRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = _get_owned_request(db, request_id, current_user)
    selected_plan = next((plan for plan in request.plans if plan.is_selected), None)
    if selected_plan is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a plan before rating")
    if selected_plan.rating is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected plan already rated")

    rating = PlanRating(
        plan_id=selected_plan.id,
        user_id=current_user.id,
        score=body.score,
        comment=body.comment,
        would_repeat=body.would_repeat,
    )
    request.status = HangoutStatus.COMPLETED
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating
