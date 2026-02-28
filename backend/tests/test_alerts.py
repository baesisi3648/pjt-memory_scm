# @TASK P2-R4-T1 - Alerts endpoint tests
# @TEST tests/test_alerts.py

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.alert import Alert
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(session: Session, email: str = "test@example.com") -> User:
    """Insert a test user with a known password into the DB."""
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


def _auth_header(user: User) -> dict[str, str]:
    """Generate an Authorization header with a valid JWT for the given user."""
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _create_alert(
    session: Session,
    severity: str = "warning",
    is_read: bool = False,
    company_id: int | None = None,
    title: str = "Test Alert",
    created_at: datetime | None = None,
) -> Alert:
    """Insert a test alert into the DB."""
    alert = Alert(
        severity=severity,
        title=title,
        description="Test description",
        is_read=is_read,
        company_id=company_id,
        created_at=created_at or datetime.utcnow(),
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


# ---------------------------------------------------------------------------
# GET /api/v1/alerts
# ---------------------------------------------------------------------------

class TestListAlerts:
    """Tests for GET /api/v1/alerts."""

    def test_list_alerts_success(self, client: TestClient, session: Session):
        """Authenticated request returns all alerts."""
        user = _create_test_user(session)
        _create_alert(session, severity="critical", title="Alert 1")
        _create_alert(session, severity="warning", title="Alert 2")

        response = client.get("/api/v1/alerts", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_alerts_filter_by_severity(self, client: TestClient, session: Session):
        """Filter alerts by severity returns only matching alerts."""
        user = _create_test_user(session)
        _create_alert(session, severity="critical", title="Critical Alert")
        _create_alert(session, severity="warning", title="Warning Alert")
        _create_alert(session, severity="info", title="Info Alert")

        response = client.get(
            "/api/v1/alerts",
            params={"severity": "critical"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["severity"] == "critical"
        assert data[0]["title"] == "Critical Alert"

    def test_list_alerts_filter_by_is_read(self, client: TestClient, session: Session):
        """Filter alerts by is_read status."""
        user = _create_test_user(session)
        _create_alert(session, is_read=False, title="Unread Alert")
        _create_alert(session, is_read=True, title="Read Alert")

        response = client.get(
            "/api/v1/alerts",
            params={"is_read": "false"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_read"] is False
        assert data[0]["title"] == "Unread Alert"

    def test_list_alerts_ordered_by_created_at_desc(self, client: TestClient, session: Session):
        """Alerts are returned in descending order by created_at."""
        user = _create_test_user(session)
        now = datetime.utcnow()
        _create_alert(session, title="Older", created_at=now - timedelta(hours=2))
        _create_alert(session, title="Newer", created_at=now)

        response = client.get("/api/v1/alerts", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Newer"
        assert data[1]["title"] == "Older"

    def test_list_alerts_unauthenticated(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/v1/alerts/{id}/read
# ---------------------------------------------------------------------------

class TestMarkAlertAsRead:
    """Tests for PATCH /api/v1/alerts/{id}/read."""

    def test_mark_alert_as_read_success(self, client: TestClient, session: Session):
        """Marking an alert as read sets is_read=True and returns the alert."""
        user = _create_test_user(session)
        alert = _create_alert(session, is_read=False)

        response = client.patch(
            f"/api/v1/alerts/{alert.id}/read",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert.id
        assert data["is_read"] is True

    def test_mark_alert_as_read_not_found(self, client: TestClient, session: Session):
        """Marking a non-existent alert returns 404."""
        user = _create_test_user(session)

        response = client.patch(
            "/api/v1/alerts/99999/read",
            headers=_auth_header(user),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Alert not found"

    def test_mark_alert_as_read_unauthenticated(self, client: TestClient, session: Session):
        """Request without token returns 401."""
        alert = _create_alert(session)
        response = client.patch(f"/api/v1/alerts/{alert.id}/read")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/companies/{company_id}/alerts
# ---------------------------------------------------------------------------

class TestCompanyAlerts:
    """Tests for GET /api/v1/companies/{company_id}/alerts."""

    def test_company_alerts_success(self, client: TestClient, session: Session):
        """Returns only alerts belonging to the specified company."""
        user = _create_test_user(session)
        _create_alert(session, company_id=1, title="Company 1 Alert")
        _create_alert(session, company_id=2, title="Company 2 Alert")
        _create_alert(session, company_id=1, title="Company 1 Alert 2")

        response = client.get(
            "/api/v1/companies/1/alerts",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for item in data:
            assert item["company_id"] == 1

    def test_company_alerts_empty(self, client: TestClient, session: Session):
        """Company with no alerts returns empty list."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/companies/999/alerts",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []
