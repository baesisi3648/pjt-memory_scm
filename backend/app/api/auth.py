# @TASK P1-R1-T1 - Auth API endpoints
# @SPEC docs/planning/02-trd.md#authentication-api
# @TEST tests/test_auth.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.rate_limit import LOGIN_LIMIT, limiter
from app.core.security import (
    create_access_token,
    get_current_user,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter()


# @TASK P1-R1-T1.1 - Login endpoint
# Rate-limited to 5 requests/minute per IP to prevent brute-force attacks.
@router.post("/login", response_model=TokenResponse)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    body: LoginRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """
    Authenticate user with email and password, return JWT access token.

    Layer 1: Input validation via Pydantic (LoginRequest)
    Layer 2: Domain validation (user exists, password matches)
    Layer 4: Error responses with appropriate status codes
    """
    user = session.exec(select(User).where(User.email == body.email)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token)


# @TASK P1-R1-T1.2 - Get current user endpoint
@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Return the currently authenticated user's information.

    Requires valid JWT Bearer token in Authorization header.
    """
    return current_user
