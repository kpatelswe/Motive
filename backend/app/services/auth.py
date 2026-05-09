from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def exchange_google_code(code: str) -> dict:
    with httpx.Client() as client:
        token_resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        userinfo_resp = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()


def get_or_create_user(db: Session, google_user: dict) -> User:
    user = db.query(User).filter(User.google_id == google_user["id"]).first()
    if user:
        user.display_name = google_user.get("name", user.display_name)
        user.avatar_url = google_user.get("picture", user.avatar_url)
        db.commit()
        db.refresh(user)
        return user

    user = User(
        google_id=google_user["id"],
        email=google_user["email"],
        display_name=google_user.get("name", google_user["email"]),
        avatar_url=google_user.get("picture"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_access_token(user_id: UUID) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise ValueError("Invalid token")
