from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import GoogleAuthRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.auth import create_access_token, exchange_google_code, get_or_create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        google_user = exchange_google_code(body.code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Google auth code",
        )

    user = get_or_create_user(db, google_user)
    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )
