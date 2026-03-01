# @TASK PERF-2 - Dashboard unified endpoint tests
# @TEST tests/test_dashboard.py

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.alert import Alert
from app.models.cluster import Cluster
from app.models.company import Company
from app.models.company_relation import CompanyRelation
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(session: Session) -> User:
    """Insert a test user and return it."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        name="Test User",
        role="analyst",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _auth_header(user: User) -> dict:
    """Build an Authorization header for the given user."""
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _seed_full_dashboard(session: Session) -> dict:
    """Seed clusters, companies, relations, and alerts for dashboard tests.

    Returns a dict with all created entities for assertion convenience.
    """
    # Clusters
    cluster_fab = Cluster(name="FAB", tier="fab")
    cluster_pkg = Cluster(name="Packaging", tier="packaging")
    session.add_all([cluster_fab, cluster_pkg])
    session.commit()
    session.refresh(cluster_fab)
    session.refresh(cluster_pkg)

    # Companies
    samsung = Company(
        name="Samsung", tier="tier1", cluster_id=cluster_fab.id, country="KR",
    )
    sk_hynix = Company(
        name="SK Hynix", tier="tier1", cluster_id=cluster_fab.id, country="KR",
    )
    ase = Company(
        name="ASE Group", tier="tier2", cluster_id=cluster_pkg.id, country="TW",
    )
    session.add_all([samsung, sk_hynix, ase])
    session.commit()
    for c in [samsung, sk_hynix, ase]:
        session.refresh(c)

    # Relations
    rel1 = CompanyRelation(
        source_id=samsung.id,
        target_id=ase.id,
        relation_type="supplier",
        strength=0.8,
    )
    rel2 = CompanyRelation(
        source_id=sk_hynix.id,
        target_id=ase.id,
        relation_type="supplier",
        strength=0.6,
    )
    session.add_all([rel1, rel2])
    session.commit()
    session.refresh(rel1)
    session.refresh(rel2)

    # Alerts (2 unread, 1 read)
    alert_unread1 = Alert(
        company_id=samsung.id,
        severity="critical",
        title="Supply shortage detected",
        is_read=False,
    )
    alert_unread2 = Alert(
        company_id=sk_hynix.id,
        severity="warning",
        title="Price fluctuation warning",
        is_read=False,
    )
    alert_read = Alert(
        company_id=ase.id,
        severity="info",
        title="Quarterly report available",
        is_read=True,
    )
    session.add_all([alert_unread1, alert_unread2, alert_read])
    session.commit()
    for a in [alert_unread1, alert_unread2, alert_read]:
        session.refresh(a)

    return {
        "clusters": [cluster_fab, cluster_pkg],
        "companies": [samsung, sk_hynix, ase],
        "relations": [rel1, rel2],
        "alerts_unread": [alert_unread1, alert_unread2],
        "alerts_read": [alert_read],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard
# ---------------------------------------------------------------------------

class TestGetDashboard:
    """Tests for GET /api/v1/dashboard."""

    def test_returns_all_data_sources(self, client: TestClient, session: Session):
        """Dashboard returns companies, clusters, relations, and unread alerts."""
        user = _create_test_user(session)
        seed = _seed_full_dashboard(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()

        # All 4 keys present
        assert "companies" in data
        assert "clusters" in data
        assert "relations" in data
        assert "alerts" in data

        # Correct counts
        assert len(data["companies"]) == 3
        assert len(data["clusters"]) == 2
        assert len(data["relations"]) == 2

    def test_only_unread_alerts(self, client: TestClient, session: Session):
        """Dashboard only includes unread alerts, not read ones."""
        user = _create_test_user(session)
        seed = _seed_full_dashboard(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()

        # Only 2 unread alerts (the read one is excluded)
        assert len(data["alerts"]) == 2
        alert_titles = {a["title"] for a in data["alerts"]}
        assert "Supply shortage detected" in alert_titles
        assert "Price fluctuation warning" in alert_titles
        assert "Quarterly report available" not in alert_titles

    def test_empty_database(self, client: TestClient, session: Session):
        """Dashboard returns empty lists when no data exists."""
        user = _create_test_user(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert data["companies"] == []
        assert data["clusters"] == []
        assert data["relations"] == []
        assert data["alerts"] == []

    def test_company_fields(self, client: TestClient, session: Session):
        """Company objects in dashboard have expected fields."""
        user = _create_test_user(session)
        _seed_full_dashboard(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))
        data = response.json()

        company = data["companies"][0]
        assert "id" in company
        assert "name" in company
        assert "cluster_id" in company
        assert "tier" in company
        assert "created_at" in company
        assert "updated_at" in company

    def test_cluster_fields(self, client: TestClient, session: Session):
        """Cluster objects in dashboard have expected fields."""
        user = _create_test_user(session)
        _seed_full_dashboard(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))
        data = response.json()

        cluster = data["clusters"][0]
        assert "id" in cluster
        assert "name" in cluster
        assert "tier" in cluster

    def test_relation_fields(self, client: TestClient, session: Session):
        """Relation objects in dashboard have expected fields."""
        user = _create_test_user(session)
        _seed_full_dashboard(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))
        data = response.json()

        relation = data["relations"][0]
        assert "id" in relation
        assert "source_id" in relation
        assert "target_id" in relation
        assert "relation_type" in relation

    def test_alert_fields(self, client: TestClient, session: Session):
        """Alert objects in dashboard have expected fields."""
        user = _create_test_user(session)
        _seed_full_dashboard(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))
        data = response.json()

        alert = data["alerts"][0]
        assert "id" in alert
        assert "company_id" in alert
        assert "severity" in alert
        assert "title" in alert
        assert "is_read" in alert
        assert "created_at" in alert

    @patch("app.api.dashboard.get_cached")
    @patch("app.api.dashboard.set_cached")
    def test_cache_miss_stores_result(
        self, mock_set_cached, mock_get_cached, client: TestClient, session: Session,
    ):
        """On cache miss, the endpoint queries DB and stores the result."""
        mock_get_cached.return_value = None
        user = _create_test_user(session)
        _seed_full_dashboard(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))

        assert response.status_code == 200
        mock_get_cached.assert_called_once()
        mock_set_cached.assert_called_once()

    @patch("app.api.dashboard.get_cached")
    def test_cache_hit_returns_cached(
        self, mock_get_cached, client: TestClient, session: Session,
    ):
        """On cache hit, the endpoint returns cached data without hitting DB."""
        from app.schemas.dashboard import DashboardResponse

        cached_response = DashboardResponse(
            companies=[], clusters=[], relations=[], alerts=[],
        )
        mock_get_cached.return_value = cached_response
        user = _create_test_user(session)

        response = client.get("/api/v1/dashboard", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert data["companies"] == []
        assert data["clusters"] == []
        assert data["relations"] == []
        assert data["alerts"] == []
