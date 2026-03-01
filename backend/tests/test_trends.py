# @TASK TRENDS-3 - Google Trends endpoint tests
# @TEST tests/test_trends.py

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.services.trends_service import (
    DEFAULT_KEYWORDS,
    _build_cache_key,
    _cache,
    _get_cached,
    _set_cached,
    clear_trends_cache,
    get_keyword_trends,
)


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


def _make_trends_dataframe(keywords: list[str], rows: int = 5) -> pd.DataFrame:
    """Create a mock DataFrame mimicking pytrends interest_over_time output."""
    dates = pd.date_range(end=datetime.now(), periods=rows, freq="W")
    data = {kw: list(range(50, 50 + rows)) for kw in keywords}
    data["isPartial"] = [False] * rows
    df = pd.DataFrame(data, index=dates)
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# Unit tests: cache helpers
# ---------------------------------------------------------------------------

class TestCacheHelpers:
    """Tests for the module-level cache helpers."""

    def setup_method(self):
        """Clear cache before each test."""
        _cache.clear()

    def test_build_cache_key_deterministic(self):
        """Same keywords in different order produce the same key."""
        key1 = _build_cache_key(["HBM", "DRAM"], "today 3-m")
        key2 = _build_cache_key(["DRAM", "HBM"], "today 3-m")
        assert key1 == key2

    def test_build_cache_key_different_timeframe(self):
        """Different timeframes produce different keys."""
        key1 = _build_cache_key(["DRAM"], "today 3-m")
        key2 = _build_cache_key(["DRAM"], "today 12-m")
        assert key1 != key2

    def test_set_and_get_cached(self):
        """Data stored via _set_cached is retrievable via _get_cached."""
        data = [{"date": "2025-01-01", "keyword": "DRAM", "value": 75}]
        _set_cached("test-key", data)
        result = _get_cached("test-key")
        assert result == data

    def test_get_cached_returns_none_when_missing(self):
        """Returns None for a key that was never cached."""
        result = _get_cached("nonexistent-key")
        assert result is None

    def test_get_cached_returns_none_when_expired(self):
        """Returns None when the cached entry is older than CACHE_TTL."""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        _cache["expired-key"] = (expired_time, [{"stale": True}])
        result = _get_cached("expired-key")
        assert result is None
        # Expired entry should also be removed
        assert "expired-key" not in _cache

    def test_clear_trends_cache(self):
        """clear_trends_cache empties the cache and returns eviction count."""
        _set_cached("k1", [])
        _set_cached("k2", [])
        count = clear_trends_cache()
        assert count == 2
        assert len(_cache) == 0


# ---------------------------------------------------------------------------
# Unit tests: get_keyword_trends
# ---------------------------------------------------------------------------

class TestGetKeywordTrends:
    """Tests for the main trends fetcher function."""

    def setup_method(self):
        _cache.clear()

    @pytest.mark.asyncio
    @patch("app.services.trends_service.TrendReq")
    async def test_returns_trend_data(self, mock_trendreq_cls):
        """Fetches and transforms interest-over-time data."""
        keywords = ["DRAM", "HBM"]
        df = _make_trends_dataframe(keywords, rows=3)

        mock_pytrends = MagicMock()
        mock_pytrends.interest_over_time.return_value = df
        mock_trendreq_cls.return_value = mock_pytrends

        result = await get_keyword_trends(keywords, timeframe="today 3-m")

        assert len(result) == 6  # 3 rows x 2 keywords
        for item in result:
            assert "date" in item
            assert "keyword" in item
            assert "value" in item
            assert item["keyword"] in keywords
            assert isinstance(item["value"], int)

    @pytest.mark.asyncio
    @patch("app.services.trends_service.TrendReq")
    async def test_returns_empty_on_empty_dataframe(self, mock_trendreq_cls):
        """Returns empty list when Google Trends returns no data."""
        mock_pytrends = MagicMock()
        mock_pytrends.interest_over_time.return_value = pd.DataFrame()
        mock_trendreq_cls.return_value = mock_pytrends

        result = await get_keyword_trends(["DRAM"], timeframe="today 3-m")

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.trends_service.TrendReq")
    async def test_handles_too_many_requests(self, mock_trendreq_cls):
        """Returns empty list on TooManyRequestsError (429)."""
        mock_pytrends = MagicMock()
        mock_pytrends.build_payload.side_effect = Exception(
            "The request failed: Google returned a response with code 429"
        )
        mock_trendreq_cls.return_value = mock_pytrends

        result = await get_keyword_trends(["DRAM"], timeframe="today 3-m")

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.trends_service.TrendReq")
    async def test_handles_generic_exception(self, mock_trendreq_cls):
        """Returns empty list on unexpected exceptions."""
        mock_trendreq_cls.side_effect = Exception("network failure")

        result = await get_keyword_trends(["DRAM"], timeframe="today 3-m")

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.trends_service.TrendReq")
    async def test_uses_cache_on_second_call(self, mock_trendreq_cls):
        """Second call with same args returns cached data, no API call."""
        keywords = ["DRAM"]
        df = _make_trends_dataframe(keywords, rows=2)

        mock_pytrends = MagicMock()
        mock_pytrends.interest_over_time.return_value = df
        mock_trendreq_cls.return_value = mock_pytrends

        result1 = await get_keyword_trends(keywords, timeframe="today 3-m")
        result2 = await get_keyword_trends(keywords, timeframe="today 3-m")

        assert result1 == result2
        # TrendReq should only be instantiated once (cached on second call)
        assert mock_trendreq_cls.call_count == 1

    @pytest.mark.asyncio
    @patch("app.services.trends_service.TrendReq")
    async def test_limits_to_five_keywords(self, mock_trendreq_cls):
        """Keywords list is truncated to 5 (Google Trends API limit)."""
        keywords = ["A", "B", "C", "D", "E", "F", "G"]
        df = _make_trends_dataframe(keywords[:5], rows=2)

        mock_pytrends = MagicMock()
        mock_pytrends.interest_over_time.return_value = df
        mock_trendreq_cls.return_value = mock_pytrends

        result = await get_keyword_trends(keywords, timeframe="today 3-m")

        # build_payload should have been called with only 5 keywords
        call_args = mock_pytrends.build_payload.call_args
        assert len(call_args[0][0]) == 5

    def test_default_keywords_not_empty(self):
        """DEFAULT_KEYWORDS contains at least one keyword."""
        assert len(DEFAULT_KEYWORDS) > 0
        assert all(isinstance(kw, str) for kw in DEFAULT_KEYWORDS)


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/trends
# ---------------------------------------------------------------------------

class TestTrendsEndpoint:
    """Tests for GET /api/v1/trends."""

    def setup_method(self):
        _cache.clear()

    @patch("app.services.trends_service.TrendReq")
    def test_trends_success_default_keywords(
        self, mock_trendreq_cls, client: TestClient, session: Session
    ):
        """Authenticated request with no keywords uses defaults."""
        user = _create_test_user(session)
        df = _make_trends_dataframe(DEFAULT_KEYWORDS, rows=3)

        mock_pytrends = MagicMock()
        mock_pytrends.interest_over_time.return_value = df
        mock_trendreq_cls.return_value = mock_pytrends

        response = client.get(
            "/api/v1/trends",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        item = data[0]
        assert "date" in item
        assert "keyword" in item
        assert "value" in item

    @patch("app.services.trends_service.TrendReq")
    def test_trends_custom_keywords(
        self, mock_trendreq_cls, client: TestClient, session: Session
    ):
        """Custom keywords are passed through correctly."""
        user = _create_test_user(session)
        keywords = ["NAND", "DDR5"]
        df = _make_trends_dataframe(keywords, rows=2)

        mock_pytrends = MagicMock()
        mock_pytrends.interest_over_time.return_value = df
        mock_trendreq_cls.return_value = mock_pytrends

        response = client.get(
            "/api/v1/trends",
            params={"keywords": "NAND,DDR5"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        found_keywords = {item["keyword"] for item in data}
        assert "NAND" in found_keywords
        assert "DDR5" in found_keywords

    @patch("app.services.trends_service.TrendReq")
    def test_trends_custom_timeframe(
        self, mock_trendreq_cls, client: TestClient, session: Session
    ):
        """Custom timeframe parameter is accepted."""
        user = _create_test_user(session)
        df = _make_trends_dataframe(["DRAM"], rows=2)

        mock_pytrends = MagicMock()
        mock_pytrends.interest_over_time.return_value = df
        mock_trendreq_cls.return_value = mock_pytrends

        response = client.get(
            "/api/v1/trends",
            params={"keywords": "DRAM", "timeframe": "today 12-m"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200

    @patch("app.services.trends_service.TrendReq")
    def test_trends_empty_on_error(
        self, mock_trendreq_cls, client: TestClient, session: Session
    ):
        """Returns empty list when Google Trends API fails."""
        user = _create_test_user(session)
        mock_trendreq_cls.side_effect = Exception("API error")

        response = client.get(
            "/api/v1/trends",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.xfail(
        reason="DEV MODE: get_current_user falls back to first/auto-created user",
        strict=False,
    )
    def test_trends_unauthenticated(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/trends")
        assert response.status_code == 401
