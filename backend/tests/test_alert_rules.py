# @TASK P2-R7-T1 - Alert Rules endpoint tests
# @TEST tests/test_alert_rules.py

import json

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.alert_rule import AlertRule
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(
    session: Session,
    email: str = "rule-user@example.com",
) -> User:
    """Insert a test user with a known password into the DB."""
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        name="Rule Test User",
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


def _create_rule_in_db(
    session: Session,
    user: User,
    name: str = "Price Alert",
    condition: dict | None = None,
    is_active: bool = True,
) -> AlertRule:
    """Insert an AlertRule directly into the DB."""
    rule = AlertRule(
        user_id=user.id,
        name=name,
        condition=json.dumps(condition or {"metric": "price", "threshold": 100}),
        is_active=is_active,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# GET /api/v1/alert-rules
# ---------------------------------------------------------------------------

class TestListAlertRules:
    """Tests for GET /api/v1/alert-rules."""

    def test_list_rules_empty(self, client: TestClient, session: Session):
        """Authenticated user with no rules gets an empty list."""
        user = _create_test_user(session, email="list-empty@example.com")

        response = client.get("/api/v1/alert-rules", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["items"] == []

    def test_list_rules_returns_own_rules(
        self, client: TestClient, session: Session
    ):
        """Authenticated user sees only their own rules."""
        user = _create_test_user(session, email="list-user@example.com")
        other = _create_test_user(session, email="list-other@example.com")

        _create_rule_in_db(session, user, name="My Rule")
        _create_rule_in_db(session, other, name="Other Rule")

        response = client.get("/api/v1/alert-rules", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "My Rule"
        assert data["items"][0]["user_id"] == user.id

    def test_list_rules_unauthenticated(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/alert-rules")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/alert-rules
# ---------------------------------------------------------------------------

class TestCreateAlertRule:
    """Tests for POST /api/v1/alert-rules."""

    def test_create_rule_success(self, client: TestClient, session: Session):
        """Create a rule and verify the response."""
        user = _create_test_user(session, email="create-rule@example.com")

        response = client.post(
            "/api/v1/alert-rules",
            headers=_auth_header(user),
            json={
                "name": "High Price Alert",
                "condition": {"metric": "price", "op": ">", "value": 500},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "High Price Alert"
        assert data["condition"] == {"metric": "price", "op": ">", "value": 500}
        assert data["is_active"] is True
        assert data["user_id"] == user.id
        assert "id" in data

    def test_create_rule_unauthenticated(self, client: TestClient):
        """Creating a rule without auth returns 401."""
        response = client.post(
            "/api/v1/alert-rules",
            json={"name": "Test", "condition": {}},
        )
        assert response.status_code == 401

    def test_create_rule_missing_fields(
        self, client: TestClient, session: Session
    ):
        """Missing required fields return 422."""
        user = _create_test_user(session, email="create-rule-422@example.com")

        response = client.post(
            "/api/v1/alert-rules",
            headers=_auth_header(user),
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/v1/alert-rules/{id}
# ---------------------------------------------------------------------------

class TestUpdateAlertRule:
    """Tests for PUT /api/v1/alert-rules/{id}."""

    def test_update_own_rule(self, client: TestClient, session: Session):
        """Owner can update their own rule."""
        user = _create_test_user(session, email="upd-owner@example.com")
        rule = _create_rule_in_db(session, user)

        response = client.put(
            f"/api/v1/alert-rules/{rule.id}",
            headers=_auth_header(user),
            json={
                "name": "Updated Rule",
                "condition": {"metric": "volume", "threshold": 200},
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Rule"
        assert data["condition"] == {"metric": "volume", "threshold": 200}
        assert data["is_active"] is False

    def test_update_other_users_rule_returns_403(
        self, client: TestClient, session: Session
    ):
        """Attempting to update another user's rule returns 403."""
        owner = _create_test_user(session, email="upd-rule-owner@example.com")
        intruder = _create_test_user(session, email="upd-rule-intruder@example.com")
        rule = _create_rule_in_db(session, owner)

        response = client.put(
            f"/api/v1/alert-rules/{rule.id}",
            headers=_auth_header(intruder),
            json={
                "name": "Hacked",
                "condition": {"metric": "hack"},
                "is_active": True,
            },
        )

        assert response.status_code == 403

    def test_update_nonexistent_rule_returns_404(
        self, client: TestClient, session: Session
    ):
        """Updating a rule that doesn't exist returns 404."""
        user = _create_test_user(session, email="upd-ghost@example.com")

        response = client.put(
            "/api/v1/alert-rules/99999",
            headers=_auth_header(user),
            json={
                "name": "Ghost",
                "condition": {},
                "is_active": True,
            },
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/alert-rules/{id}/toggle
# ---------------------------------------------------------------------------

class TestToggleAlertRule:
    """Tests for PATCH /api/v1/alert-rules/{id}/toggle."""

    def test_toggle_active_to_inactive(
        self, client: TestClient, session: Session
    ):
        """Toggle an active rule to inactive."""
        user = _create_test_user(session, email="toggle-on@example.com")
        rule = _create_rule_in_db(session, user, is_active=True)

        response = client.patch(
            f"/api/v1/alert-rules/{rule.id}/toggle",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_toggle_inactive_to_active(
        self, client: TestClient, session: Session
    ):
        """Toggle an inactive rule to active."""
        user = _create_test_user(session, email="toggle-off@example.com")
        rule = _create_rule_in_db(session, user, is_active=False)

        response = client.patch(
            f"/api/v1/alert-rules/{rule.id}/toggle",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_toggle_other_users_rule_returns_403(
        self, client: TestClient, session: Session
    ):
        """Toggling another user's rule returns 403."""
        owner = _create_test_user(session, email="toggle-owner@example.com")
        intruder = _create_test_user(session, email="toggle-intruder@example.com")
        rule = _create_rule_in_db(session, owner)

        response = client.patch(
            f"/api/v1/alert-rules/{rule.id}/toggle",
            headers=_auth_header(intruder),
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/v1/alert-rules/{id}
# ---------------------------------------------------------------------------

class TestDeleteAlertRule:
    """Tests for DELETE /api/v1/alert-rules/{id}."""

    def test_delete_own_rule(self, client: TestClient, session: Session):
        """Owner can delete their own rule."""
        user = _create_test_user(session, email="del-owner@example.com")
        rule = _create_rule_in_db(session, user)

        response = client.delete(
            f"/api/v1/alert-rules/{rule.id}",
            headers=_auth_header(user),
        )

        assert response.status_code == 204

        # Verify it's gone
        response = client.get("/api/v1/alert-rules", headers=_auth_header(user))
        data = response.json()
        assert data["count"] == 0
        assert data["items"] == []

    def test_delete_other_users_rule_returns_403(
        self, client: TestClient, session: Session
    ):
        """Attempting to delete another user's rule returns 403."""
        owner = _create_test_user(session, email="del-rule-owner@example.com")
        intruder = _create_test_user(session, email="del-rule-intruder@example.com")
        rule = _create_rule_in_db(session, owner)

        response = client.delete(
            f"/api/v1/alert-rules/{rule.id}",
            headers=_auth_header(intruder),
        )

        assert response.status_code == 403

    def test_delete_nonexistent_rule_returns_404(
        self, client: TestClient, session: Session
    ):
        """Deleting a rule that doesn't exist returns 404."""
        user = _create_test_user(session, email="del-ghost@example.com")

        response = client.delete(
            "/api/v1/alert-rules/99999",
            headers=_auth_header(user),
        )

        assert response.status_code == 404

    def test_delete_rule_unauthenticated(self, client: TestClient):
        """Deleting without auth returns 401."""
        response = client.delete("/api/v1/alert-rules/1")
        assert response.status_code == 401
