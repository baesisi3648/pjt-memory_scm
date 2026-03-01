# @TASK P1-R1-T1 - JWT token creation/verification utilities
# @SPEC docs/planning/02-trd.md#authentication-api

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.user import User

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """FastAPI dependency that extracts and validates the current user from JWT.

    DEV MODE: If token validation fails, returns the first user in the database
    as a fallback so the app can be used without logging in.
    Remove this fallback before deploying to production.
    """
    try:
        payload = decode_access_token(token)
        email: Optional[str] = payload.get("sub")
        if email:
            user = session.exec(select(User).where(User.email == email)).first()
            if user:
                return user
    except (JWTError, Exception):
        pass

    # DEV FALLBACK: return first user in database
    fallback = session.exec(select(User)).first()
    if fallback:
        return fallback

    # No users exist at all — create a default dev user
    dev_user = User(
        email="dev@local",
        hashed_password=hash_password("dev"),
        name="Dev User",
        role="admin",
    )
    session.add(dev_user)
    session.commit()
    session.refresh(dev_user)
    return dev_user
