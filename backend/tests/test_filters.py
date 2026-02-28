# @TASK P2-R6-T1 - User Filters endpoint tests
# @TEST tests/test_filters.py

import json

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.user_filter import UserFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(
    session: Session,
    email: str = "filter-user@example.com",
) -> User:
    """Insert a test user with a known password into the DB."""
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        name="Filter Test User",
        role="analyst",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _auth_header(user: User) -> dict[str, str]:
    """Build an Authorization header for the given user."""
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _create_filter_in_db(
    session: Session,
    user: User,
    name: str = "My Filter",
    company_ids: list[int] | None = None,
    is_default: bool = False,
) -> UserFilter:
    """Insert a UserFilter directly into the DB."""
    user_filter = UserFilter(
        user_id=user.id,
        name=name,
        company_ids=json.dumps(company_ids or [1, 2, 3]),
        is_default=is_default,
    )
    session.add(user_filter)
    session.commit()
    session.refresh(user_filter)
    return user_filter


# ---------------------------------------------------------------------------
# GET /api/v1/filters
# ---------------------------------------------------------------------------

class TestListFilters:
    """Tests for GET /api/v1/filters."""

    def test_list_filters_empty(self, client: TestClient, session: Session):
        """Authenticated user with no filters gets an empty list."""
        user = _create_test_user(session, email="f-list-empty@example.com")

        response = client.get("/api/v1/filters", headers=_auth_header(user))

        assert response.status_code == 200
        assert response.json() == []

    def test_list_filters_returns_own_filters(
        self, client: TestClient, session: Session
    ):
        """Authenticated user sees only their own filters."""
        user = _create_test_user(session, email="f-list-user@example.com")
        other = _create_test_user(session, email="f-list-other@example.com")

        _create_filter_in_db(session, user, name="My Filter")
        _create_filter_in_db(session, other, name="Other Filter")

        response = client.get("/api/v1/filters", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "My Filter"
        assert data[0]["user_id"] == user.id

    def test_list_filters_unauthenticated(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/filters")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/filters
# ---------------------------------------------------------------------------

class TestCreateFilter:
    """Tests for POST /api/v1/filters."""

    def test_create_filter_success(self, client: TestClient, session: Session):
        """Create a filter and verify the response."""
        user = _create_test_user(session, email="f-create@example.com")

        response = client.post(
            "/api/v1/filters",
            headers=_auth_header(user),
            json={"name": "Samsung Only", "company_ids": [10, 20], "is_default": True},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Samsung Only"
        assert data["company_ids"] == [10, 20]
        assert data["is_default"] is True
        assert data["user_id"] == user.id
        assert "id" in data

    def test_create_filter_default_is_false(
        self, client: TestClient, session: Session
    ):
        """is_default defaults to False when not provided."""
        user = _create_test_user(session, email="f-create-default@example.com")

        response = client.post(
            "/api/v1/filters",
            headers=_auth_header(user),
            json={"name": "Basic", "company_ids": [1]},
        )

        assert response.status_code == 201
        assert response.json()["is_default"] is False

    def test_create_filter_unauthenticated(self, client: TestClient):
        """Creating a filter without auth returns 401."""
        response = client.post(
            "/api/v1/filters",
            json={"name": "Test", "company_ids": [1]},
        )
        assert response.status_code == 401

    def test_create_filter_missing_fields(
        self, client: TestClient, session: Session
    ):
        """Missing required fields return 422."""
        user = _create_test_user(session, email="f-create-422@example.com")

        response = client.post(
            "/api/v1/filters",
            headers=_auth_header(user),
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/filters/{id}
# ---------------------------------------------------------------------------

class TestDeleteFilter:
    """Tests for DELETE /api/v1/filters/{id}."""

    def test_delete_own_filter(self, client: TestClient, session: Session):
        """Owner can delete their own filter."""
        user = _create_test_user(session, email="f-del-owner@example.com")
        f = _create_filter_in_db(session, user)

        response = client.delete(
            f"/api/v1/filters/{f.id}",
            headers=_auth_header(user),
        )

        assert response.status_code == 204

        # Verify it's gone
        response = client.get("/api/v1/filters", headers=_auth_header(user))
        assert response.json() == []

    def test_delete_other_users_filter_returns_403(
        self, client: TestClient, session: Session
    ):
        """Attempting to delete another user's filter returns 403."""
        owner = _create_test_user(session, email="f-del-rule-owner@example.com")
        intruder = _create_test_user(session, email="f-del-rule-intruder@example.com")
        f = _create_filter_in_db(session, owner)

        response = client.delete(
            f"/api/v1/filters/{f.id}",
            headers=_auth_header(intruder),
        )

        assert response.status_code == 403

    def test_delete_nonexistent_filter_returns_404(
        self, client: TestClient, session: Session
    ):
        """Deleting a filter that doesn't exist returns 404."""
        user = _create_test_user(session, email="f-del-ghost@example.com")

        response = client.delete(
            "/api/v1/filters/99999",
            headers=_auth_header(user),
        )

        assert response.status_code == 404

    def test_delete_filter_unauthenticated(self, client: TestClient):
        """Deleting without auth returns 401."""
        response = client.delete("/api/v1/filters/1")
        assert response.status_code == 401
