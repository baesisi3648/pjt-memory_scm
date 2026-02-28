# @TASK STOCK-T3 - Stock endpoint tests
# @TEST tests/test_stock.py

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.cluster import Cluster
from app.models.company import Company
from app.models.user import User
from app.services.stock_service import StockData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(session: Session) -> User:
    """Insert a test user and return it."""
    user = User(
        email="stock_test@example.com",
        hashed_password=hash_password("password123"),
        name="Stock Test User",
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


def _seed_company_with_ticker(session: Session, ticker: str | None = "ASML") -> Company:
    """Create a sample cluster and company with a ticker."""
    cluster = Cluster(name="Equipment", tier="equipment")
    session.add(cluster)
    session.commit()
    session.refresh(cluster)

    company = Company(
        name="Test Corp",
        name_kr="Test Corp KR",
        tier="equipment",
        cluster_id=cluster.id,
        country="US",
        ticker=ticker,
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


# ---------------------------------------------------------------------------
# GET /api/v1/companies/{id}/stock
# ---------------------------------------------------------------------------

class TestGetCompanyStock:
    """Tests for GET /api/v1/companies/{id}/stock."""

    def test_stock_not_found_company(self, client: TestClient, session: Session):
        """Non-existent company returns 404."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/companies/99999/stock",
            headers=_auth_header(user),
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_stock_no_ticker(self, client: TestClient, session: Session):
        """Company without ticker returns { ticker: null }."""
        user = _create_test_user(session)
        company = _seed_company_with_ticker(session, ticker=None)

        response = client.get(
            f"/api/v1/companies/{company.id}/stock",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] is None
        assert data["price"] is None

    @patch("app.api.stock.fetch_stock_data")
    def test_stock_success(self, mock_fetch, client: TestClient, session: Session):
        """Company with valid ticker returns stock data."""
        user = _create_test_user(session)
        company = _seed_company_with_ticker(session, ticker="ASML")

        mock_fetch.return_value = StockData(
            current_price=850.50,
            change_percent=2.35,
            currency="USD",
            market_cap=350_000_000_000,
        )

        response = client.get(
            f"/api/v1/companies/{company.id}/stock",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "ASML"
        assert data["price"] == 850.50
        assert data["change_percent"] == 2.35
        assert data["currency"] == "USD"
        assert data["market_cap"] == 350_000_000_000
        assert data["updated_at"] is not None
        mock_fetch.assert_called_once_with("ASML")

    @patch("app.api.stock.fetch_stock_data")
    def test_stock_api_failure(self, mock_fetch, client: TestClient, session: Session):
        """When stock API fails, return ticker but no price data."""
        user = _create_test_user(session)
        company = _seed_company_with_ticker(session, ticker="INVALID")

        mock_fetch.return_value = None

        response = client.get(
            f"/api/v1/companies/{company.id}/stock",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "INVALID"
        assert data["price"] is None
        assert data["updated_at"] is not None

    def test_stock_requires_auth(self, client: TestClient, session: Session):
        """Unauthenticated request returns 401."""
        company = _seed_company_with_ticker(session, ticker="ASML")

        response = client.get(f"/api/v1/companies/{company.id}/stock")

        assert response.status_code == 401
