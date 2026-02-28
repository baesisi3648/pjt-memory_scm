# @TASK P1-R1-T1 - Auth Pydantic schemas
# @SPEC docs/planning/02-trd.md#authentication-api

from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Response body for successful login."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response body for GET /auth/me."""

    id: int
    email: str
    name: str | None = None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
