# @TASK P2-R2-T1 - Clusters endpoint tests
# @TEST tests/test_clusters.py

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


def _seed_clusters_and_companies(session: Session) -> tuple[list[Cluster], list[Company]]:
    """Create sample clusters (with parent-child) and companies."""
    parent = Cluster(name="Manufacturing", tier="manufacturing")
    session.add(parent)
    session.commit()
    session.refresh(parent)

    child1 = Cluster(name="FAB", tier="fab", parent_id=parent.id)
    child2 = Cluster(name="Packaging", tier="packaging", parent_id=parent.id)
    session.add_all([child1, child2])
    session.commit()
    session.refresh(child1)
    session.refresh(child2)

    companies = [
        Company(name="Samsung", tier="tier1", cluster_id=child1.id),
        Company(name="TSMC", tier="tier1", cluster_id=child1.id),
        Company(name="ASE Group", tier="tier2", cluster_id=child2.id),
    ]
    session.add_all(companies)
    session.commit()
    for c in companies:
        session.refresh(c)

    return [parent, child1, child2], companies


# ---------------------------------------------------------------------------
# GET /api/v1/clusters
# ---------------------------------------------------------------------------

class TestListClusters:
    """Tests for GET /api/v1/clusters."""

    def test_list_all(self, client: TestClient, session: Session):
        """List all clusters with parent_id."""
        user = _create_test_user(session)
        clusters, _ = _seed_clusters_and_companies(session)

        response = client.get("/api/v1/clusters", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["items"]) == 3

        # Verify parent_id is present
        parent_item = next(
            item for item in data["items"] if item["name"] == "Manufacturing"
        )
        assert parent_item["parent_id"] is None

        child_item = next(
            item for item in data["items"] if item["name"] == "FAB"
        )
        assert child_item["parent_id"] == clusters[0].id

    def test_list_requires_auth(self, client: TestClient):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/clusters")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/clusters/{id}/companies
# ---------------------------------------------------------------------------

class TestClusterCompanies:
    """Tests for GET /api/v1/clusters/{id}/companies."""

    def test_cluster_companies(self, client: TestClient, session: Session):
        """Get companies belonging to a specific cluster."""
        user = _create_test_user(session)
        clusters, _ = _seed_clusters_and_companies(session)
        fab_cluster = clusters[1]  # FAB cluster

        response = client.get(
            f"/api/v1/clusters/{fab_cluster.id}/companies",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        names = {item["name"] for item in data["items"]}
        assert names == {"Samsung", "TSMC"}

    def test_cluster_not_found(self, client: TestClient, session: Session):
        """Non-existent cluster ID returns 404."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/clusters/99999/companies",
            headers=_auth_header(user),
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cluster_with_no_companies(self, client: TestClient, session: Session):
        """Cluster with no companies returns empty list."""
        user = _create_test_user(session)
        empty_cluster = Cluster(name="Empty", tier="empty")
        session.add(empty_cluster)
        session.commit()
        session.refresh(empty_cluster)

        response = client.get(
            f"/api/v1/clusters/{empty_cluster.id}/companies",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["items"] == []
