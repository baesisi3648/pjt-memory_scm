# @TASK P1-R1-T1 - Auth endpoint tests
# @TEST tests/test_auth.py

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(session: Session, email: str = "test@example.com") -> User:
    """Insert a test user with a known password ('password123') into the DB."""
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        name="Test User",
        role="analyst",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, client: TestClient, session: Session):
        """Valid credentials return a JWT access token."""
        _create_test_user(session)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client: TestClient, session: Session):
        """Wrong password returns 401."""
        _create_test_user(session)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_login_nonexistent_user(self, client: TestClient):
        """Non-existent email returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_login_missing_fields(self, client: TestClient):
        """Missing required fields return 422 validation error."""
        response = client.post("/api/v1/auth/login", json={})

        assert response.status_code == 422

    def test_login_returns_valid_jwt(self, client: TestClient, session: Session):
        """The returned token can be decoded and contains the user email."""
        _create_test_user(session)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        token = response.json()["access_token"]
        from app.core.security import decode_access_token

        payload = decode_access_token(token)
        assert payload["sub"] == "test@example.com"


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------

class TestGetMe:
    """Tests for GET /api/v1/auth/me."""

    def test_get_me_success(self, client: TestClient, session: Session):
        """Authenticated request returns user info."""
        user = _create_test_user(session)
        token = create_access_token(data={"sub": user.email})

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["role"] == "analyst"
        assert data["id"] == user.id
        assert "created_at" in data
        # hashed_password must NOT be in the response
        assert "hashed_password" not in data

    def test_get_me_no_token(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """Request with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-value"},
        )

        assert response.status_code == 401

    def test_get_me_expired_token(self, client: TestClient, session: Session):
        """Expired token returns 401."""
        from datetime import timedelta

        _create_test_user(session)
        token = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(seconds=-1),
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401

    def test_get_me_token_for_deleted_user(self, client: TestClient, session: Session):
        """Token for a user that no longer exists returns 401."""
        token = create_access_token(data={"sub": "deleted@example.com"})

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
