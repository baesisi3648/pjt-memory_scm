# @TASK P2-R1-T1 - Companies endpoint tests
# @TEST tests/test_companies.py

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.cluster import Cluster
from app.models.company import Company
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


def _seed_companies(session: Session) -> list[Company]:
    """Create sample clusters and companies for testing."""
    cluster1 = Cluster(name="FAB", tier="fab")
    cluster2 = Cluster(name="Packaging", tier="packaging")
    session.add_all([cluster1, cluster2])
    session.commit()
    session.refresh(cluster1)
    session.refresh(cluster2)

    companies = [
        Company(name="Samsung", tier="tier1", cluster_id=cluster1.id, country="KR"),
        Company(name="SK Hynix", tier="tier1", cluster_id=cluster1.id, country="KR"),
        Company(name="ASE Group", tier="tier2", cluster_id=cluster2.id, country="TW"),
    ]
    session.add_all(companies)
    session.commit()
    for c in companies:
        session.refresh(c)
    return companies


# ---------------------------------------------------------------------------
# GET /api/v1/companies
# ---------------------------------------------------------------------------

class TestListCompanies:
    """Tests for GET /api/v1/companies."""

    def test_list_all(self, client: TestClient, session: Session):
        """List all companies without filters."""
        user = _create_test_user(session)
        _seed_companies(session)

        response = client.get("/api/v1/companies", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["items"]) == 3

    def test_filter_by_cluster_id(self, client: TestClient, session: Session):
        """Filter companies by cluster_id."""
        user = _create_test_user(session)
        companies = _seed_companies(session)
        fab_cluster_id = companies[0].cluster_id

        response = client.get(
            f"/api/v1/companies?cluster_id={fab_cluster_id}",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        names = {item["name"] for item in data["items"]}
        assert names == {"Samsung", "SK Hynix"}

    def test_filter_by_tier(self, client: TestClient, session: Session):
        """Filter companies by tier."""
        user = _create_test_user(session)
        _seed_companies(session)

        response = client.get(
            "/api/v1/companies?tier=tier2",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "ASE Group"

    def test_filter_by_company_ids(self, client: TestClient, session: Session):
        """Filter companies by comma-separated company IDs."""
        user = _create_test_user(session)
        companies = _seed_companies(session)
        ids_param = f"{companies[0].id},{companies[2].id}"

        response = client.get(
            f"/api/v1/companies?company_ids={ids_param}",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        names = {item["name"] for item in data["items"]}
        assert names == {"Samsung", "ASE Group"}

    def test_list_requires_auth(self, client: TestClient):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/companies")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/companies/{id}
# ---------------------------------------------------------------------------

class TestGetCompany:
    """Tests for GET /api/v1/companies/{id}."""

    def test_get_detail(self, client: TestClient, session: Session):
        """Get a single company by ID."""
        user = _create_test_user(session)
        companies = _seed_companies(session)

        response = client.get(
            f"/api/v1/companies/{companies[0].id}",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Samsung"
        assert data["tier"] == "tier1"
        assert data["country"] == "KR"
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_not_found(self, client: TestClient, session: Session):
        """Non-existent company ID returns 404."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/companies/99999",
            headers=_auth_header(user),
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
