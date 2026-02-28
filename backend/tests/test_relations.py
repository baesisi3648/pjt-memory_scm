# @TASK P2-R3-T1 - Relations endpoint tests
# @TEST tests/test_relations.py

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
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


def _seed_data(session: Session) -> tuple[list[Company], list[CompanyRelation]]:
    """Create companies and relations for testing."""
    cluster = Cluster(name="FAB", tier="fab")
    session.add(cluster)
    session.commit()
    session.refresh(cluster)

    companies = [
        Company(name="Samsung", tier="tier1", cluster_id=cluster.id),
        Company(name="SK Hynix", tier="tier1", cluster_id=cluster.id),
        Company(name="ASE Group", tier="tier2", cluster_id=cluster.id),
    ]
    session.add_all(companies)
    session.commit()
    for c in companies:
        session.refresh(c)

    relations = [
        CompanyRelation(
            source_id=companies[0].id,
            target_id=companies[2].id,
            relation_type="supplier",
            strength=0.8,
        ),
        CompanyRelation(
            source_id=companies[1].id,
            target_id=companies[2].id,
            relation_type="supplier",
            strength=0.6,
        ),
        CompanyRelation(
            source_id=companies[0].id,
            target_id=companies[1].id,
            relation_type="partner",
            strength=0.5,
        ),
    ]
    session.add_all(relations)
    session.commit()
    for r in relations:
        session.refresh(r)

    return companies, relations


# ---------------------------------------------------------------------------
# GET /api/v1/relations
# ---------------------------------------------------------------------------

class TestListRelations:
    """Tests for GET /api/v1/relations."""

    def test_list_all(self, client: TestClient, session: Session):
        """List all relations without filters."""
        user = _create_test_user(session)
        _, relations = _seed_data(session)

        response = client.get("/api/v1/relations", headers=_auth_header(user))

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["items"]) == 3

    def test_filter_by_company_ids(self, client: TestClient, session: Session):
        """Filter relations by company_ids (source_id OR target_id in list)."""
        user = _create_test_user(session)
        companies, _ = _seed_data(session)
        # Filter for ASE Group only -- should get relations where ASE is source or target
        ase_id = companies[2].id

        response = client.get(
            f"/api/v1/relations?company_ids={ase_id}",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        # Samsung->ASE and SK Hynix->ASE
        assert data["count"] == 2
        for item in data["items"]:
            assert item["source_id"] == ase_id or item["target_id"] == ase_id

    def test_filter_by_multiple_company_ids(self, client: TestClient, session: Session):
        """Filter relations by multiple comma-separated company IDs."""
        user = _create_test_user(session)
        companies, _ = _seed_data(session)
        # All three companies -- should return all 3 relations
        ids_param = f"{companies[0].id},{companies[1].id}"

        response = client.get(
            f"/api/v1/relations?company_ids={ids_param}",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        # All 3 relations involve Samsung or SK Hynix
        assert data["count"] == 3

    def test_list_requires_auth(self, client: TestClient):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/relations")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/companies/{id}/relations
# ---------------------------------------------------------------------------

class TestCompanyRelations:
    """Tests for GET /api/v1/companies/{id}/relations."""

    def test_company_relations(self, client: TestClient, session: Session):
        """Get all relations for a specific company."""
        user = _create_test_user(session)
        companies, _ = _seed_data(session)
        samsung_id = companies[0].id

        response = client.get(
            f"/api/v1/companies/{samsung_id}/relations",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        # Samsung->ASE (supplier) + Samsung->SK Hynix (partner)
        assert data["count"] == 2
        for item in data["items"]:
            # Enriched format: company_id is the partner, direction shows relationship
            assert "company_id" in item
            assert "company_name" in item
            assert item["direction"] in ("upstream", "downstream")

    def test_company_not_found(self, client: TestClient, session: Session):
        """Non-existent company ID returns 404."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/companies/99999/relations",
            headers=_auth_header(user),
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_company_with_no_relations(self, client: TestClient, session: Session):
        """Company with no relations returns empty list."""
        user = _create_test_user(session)
        cluster = Cluster(name="Solo", tier="solo")
        session.add(cluster)
        session.commit()
        session.refresh(cluster)

        company = Company(name="Lonely Corp", tier="tier3", cluster_id=cluster.id)
        session.add(company)
        session.commit()
        session.refresh(company)

        response = client.get(
            f"/api/v1/companies/{company.id}/relations",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["items"] == []
