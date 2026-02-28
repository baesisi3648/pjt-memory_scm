# @TASK P2-R5-T1 - News items endpoint tests
# @TEST tests/test_news.py

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.news_item import NewsItem
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


def _create_news_item(
    session: Session,
    company_id: int = 1,
    title: str = "Test News",
    published_at: datetime | None = None,
) -> NewsItem:
    """Insert a test news item into the DB."""
    news = NewsItem(
        title=title,
        url=f"https://example.com/news/{title.lower().replace(' ', '-')}",
        source="Test Source",
        company_id=company_id,
        published_at=published_at or datetime.utcnow(),
    )
    session.add(news)
    session.commit()
    session.refresh(news)
    return news


# ---------------------------------------------------------------------------
# GET /api/v1/companies/{company_id}/news
# ---------------------------------------------------------------------------

class TestCompanyNews:
    """Tests for GET /api/v1/companies/{company_id}/news."""

    def test_company_news_list(self, client: TestClient, session: Session):
        """Returns news items for the specified company."""
        user = _create_test_user(session)
        _create_news_item(session, company_id=1, title="News A")
        _create_news_item(session, company_id=1, title="News B")
        _create_news_item(session, company_id=2, title="Other Company News")

        response = client.get(
            "/api/v1/companies/1/news",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for item in data:
            assert item["company_id"] == 1

    def test_company_news_limit_param(self, client: TestClient, session: Session):
        """The limit query param restricts the number of returned items."""
        user = _create_test_user(session)
        now = datetime.utcnow()
        for i in range(5):
            _create_news_item(
                session,
                company_id=1,
                title=f"News {i}",
                published_at=now - timedelta(hours=i),
            )

        response = client.get(
            "/api/v1/companies/1/news",
            params={"limit": 3},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_company_news_ordered_by_published_at_desc(self, client: TestClient, session: Session):
        """News items are returned in descending order by published_at."""
        user = _create_test_user(session)
        now = datetime.utcnow()
        _create_news_item(session, company_id=1, title="Older News", published_at=now - timedelta(hours=2))
        _create_news_item(session, company_id=1, title="Newer News", published_at=now)

        response = client.get(
            "/api/v1/companies/1/news",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Newer News"
        assert data[1]["title"] == "Older News"

    def test_company_news_empty_result(self, client: TestClient, session: Session):
        """Company with no news returns empty list."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/companies/999/news",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_company_news_unauthenticated(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/companies/1/news")
        assert response.status_code == 401
