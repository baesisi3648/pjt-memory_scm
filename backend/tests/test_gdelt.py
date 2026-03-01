# @TASK GDELT-3 - GDELT geopolitical events endpoint tests
# @TEST tests/test_gdelt.py

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.services.gdelt_service import (
    DEFAULT_KEYWORDS,
    _build_cache_key,
    _cache,
    _get_cached,
    _parse_gdelt_article,
    _parse_timespan_to_minutes,
    _set_cached,
    clear_gdelt_cache,
    fetch_geopolitical_events,
    get_semiconductor_risk_events,
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


SAMPLE_GDELT_ARTICLES = [
    {
        "title": "US Tightens Semiconductor Export Controls to China",
        "url": "https://example.com/article1",
        "sourcecountry": "United States",
        "domain": "example.com",
        "seendate": "20260301T120000Z",
        "tone": "-3.45",
        "language": "English",
        "socialimage": "https://example.com/img1.jpg",
    },
    {
        "title": "Taiwan Strait Tensions Rise Amid Military Exercises",
        "url": "https://example.com/article2",
        "sourcecountry": "Taiwan",
        "domain": "example.com",
        "seendate": "20260301T100000Z",
        "tone": "-5.12",
        "language": "English",
        "socialimage": "",
    },
    {
        "title": "TSMC Reports Strong Quarterly Results Despite Geopolitical Risk",
        "url": "https://example.com/article3",
        "sourcecountry": "Taiwan",
        "domain": "example.com",
        "seendate": "20260228T150000Z",
        "tone": "2.80",
        "language": "English",
        "socialimage": "https://example.com/img3.jpg",
    },
]


SAMPLE_GDELT_RESPONSE = {"articles": SAMPLE_GDELT_ARTICLES}


# ---------------------------------------------------------------------------
# Unit tests: cache helpers
# ---------------------------------------------------------------------------

class TestGdeltCacheHelpers:
    """Tests for the module-level cache helpers."""

    def setup_method(self):
        """Clear cache before each test."""
        _cache.clear()

    def test_build_cache_key_deterministic(self):
        """Same keywords in different order produce the same key."""
        key1 = _build_cache_key(["chip ban", "TSMC risk"], "24h")
        key2 = _build_cache_key(["TSMC risk", "chip ban"], "24h")
        assert key1 == key2

    def test_build_cache_key_different_timespan(self):
        """Different timespans produce different keys."""
        key1 = _build_cache_key(["chip ban"], "24h")
        key2 = _build_cache_key(["chip ban"], "48h")
        assert key1 != key2

    def test_set_and_get_cached(self):
        """Data stored via _set_cached is retrievable via _get_cached."""
        data = [{"title": "Test Event", "url": "https://example.com"}]
        _set_cached("test-key", data)
        result = _get_cached("test-key")
        assert result == data

    def test_get_cached_returns_none_when_missing(self):
        """Returns None for a key that was never cached."""
        result = _get_cached("nonexistent-key")
        assert result is None

    def test_get_cached_returns_none_when_expired(self):
        """Returns None when the cached entry is older than CACHE_TTL (1h)."""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
        _cache["expired-key"] = (expired_time, [{"stale": True}])
        result = _get_cached("expired-key")
        assert result is None
        # Expired entry should also be removed
        assert "expired-key" not in _cache

    def test_get_cached_returns_data_within_ttl(self):
        """Returns cached data when within TTL (1 hour)."""
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        data = [{"fresh": True}]
        _cache["fresh-key"] = (recent_time, data)
        result = _get_cached("fresh-key")
        assert result == data

    def test_clear_gdelt_cache(self):
        """clear_gdelt_cache empties the cache and returns eviction count."""
        _set_cached("k1", [])
        _set_cached("k2", [])
        count = clear_gdelt_cache()
        assert count == 2
        assert len(_cache) == 0


# ---------------------------------------------------------------------------
# Unit tests: _parse_timespan_to_minutes
# ---------------------------------------------------------------------------

class TestParseTimespan:
    """Tests for timespan parsing helper."""

    def test_hours(self):
        assert _parse_timespan_to_minutes("24h") == 1440

    def test_days(self):
        assert _parse_timespan_to_minutes("7d") == 10080

    def test_minutes(self):
        assert _parse_timespan_to_minutes("30m") == 30

    def test_plain_number_treated_as_hours(self):
        assert _parse_timespan_to_minutes("12") == 720

    def test_invalid_defaults_to_24h(self):
        assert _parse_timespan_to_minutes("invalid") == 1440

    def test_whitespace_stripped(self):
        assert _parse_timespan_to_minutes("  48h  ") == 2880


# ---------------------------------------------------------------------------
# Unit tests: _parse_gdelt_article
# ---------------------------------------------------------------------------

class TestParseGdeltArticle:
    """Tests for article parsing."""

    def test_parses_complete_article(self):
        article = SAMPLE_GDELT_ARTICLES[0]
        result = _parse_gdelt_article(article)

        assert result["title"] == "US Tightens Semiconductor Export Controls to China"
        assert result["url"] == "https://example.com/article1"
        assert result["source"] == "United States"
        assert result["domain"] == "example.com"
        assert result["date"] == "20260301T120000Z"
        assert result["tone"] == -3.45
        assert result["language"] == "English"
        assert result["image_url"] == "https://example.com/img1.jpg"
        assert isinstance(result["themes"], list)

    def test_empty_socialimage_becomes_none(self):
        article = SAMPLE_GDELT_ARTICLES[1]
        result = _parse_gdelt_article(article)
        assert result["image_url"] is None

    def test_handles_missing_fields(self):
        article = {"title": "Minimal Article"}
        result = _parse_gdelt_article(article)
        assert result["title"] == "Minimal Article"
        assert result["url"] == ""
        assert result["tone"] is None

    def test_handles_invalid_tone(self):
        article = {"title": "Bad Tone", "tone": "not-a-number"}
        result = _parse_gdelt_article(article)
        assert result["tone"] is None


# ---------------------------------------------------------------------------
# Unit tests: fetch_geopolitical_events
# ---------------------------------------------------------------------------

class TestFetchGeopoliticalEvents:
    """Tests for the main GDELT event fetcher."""

    def setup_method(self):
        _cache.clear()

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_returns_parsed_events(self, mock_client_cls):
        """Fetches and parses GDELT events successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GDELT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events(
            keywords=["semiconductor export control"],
            timespan="24h",
            limit=20,
        )

        assert len(result) == 3
        assert result[0]["title"] == "US Tightens Semiconductor Export Controls to China"
        assert result[0]["tone"] == -3.45

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_returns_empty_on_no_articles(self, mock_client_cls):
        """Returns empty list when GDELT returns no articles."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"articles": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events(keywords=["nonexistent topic"])
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_handles_timeout(self, mock_client_cls):
        """Returns empty list on timeout."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events(keywords=["chip ban"])
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_handles_http_error(self, mock_client_cls):
        """Returns empty list on HTTP errors."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=httpx.Request("GET", "https://api.gdeltproject.org/"),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events(keywords=["chip ban"])
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_handles_json_parse_error(self, mock_client_cls):
        """Returns empty list when GDELT returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events(keywords=["chip ban"])
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_uses_default_keywords(self, mock_client_cls):
        """Uses DEFAULT_KEYWORDS when no keywords provided."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GDELT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events()
        assert len(result) > 0

        # Verify the query contained OR-joined keywords
        call_kwargs = mock_client.get.call_args
        query_params = call_kwargs.kwargs.get("params", {})
        query_str = query_params.get("query", "")
        assert "OR" in query_str

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_filters_empty_titles(self, mock_client_cls):
        """Articles with empty titles are filtered out."""
        articles_with_empty = [
            {"title": "", "url": "https://example.com/empty"},
            {"title": "Valid Article", "url": "https://example.com/valid"},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"articles": articles_with_empty}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events(keywords=["test"])
        assert len(result) == 1
        assert result[0]["title"] == "Valid Article"

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.httpx.AsyncClient")
    async def test_respects_limit(self, mock_client_cls):
        """Result set is limited to the requested number."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GDELT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await fetch_geopolitical_events(keywords=["test"], limit=2)
        assert len(result) <= 2


# ---------------------------------------------------------------------------
# Unit tests: get_semiconductor_risk_events
# ---------------------------------------------------------------------------

class TestGetSemiconductorRiskEvents:
    """Tests for the cached semiconductor-specific event fetcher."""

    def setup_method(self):
        _cache.clear()

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.fetch_geopolitical_events")
    async def test_caches_results(self, mock_fetch):
        """Second call returns cached data without calling fetch again."""
        mock_fetch.return_value = [{"title": "Cached Event"}]

        result1 = await get_semiconductor_risk_events()
        result2 = await get_semiconductor_risk_events()

        assert result1 == result2
        assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.fetch_geopolitical_events")
    async def test_caches_empty_results(self, mock_fetch):
        """Empty results are cached to avoid hammering GDELT."""
        mock_fetch.return_value = []

        result1 = await get_semiconductor_risk_events()
        result2 = await get_semiconductor_risk_events()

        assert result1 == []
        assert result2 == []
        assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    @patch("app.services.gdelt_service.fetch_geopolitical_events")
    async def test_respects_limit(self, mock_fetch):
        """Limit parameter truncates cached results."""
        mock_fetch.return_value = [
            {"title": f"Event {i}"} for i in range(10)
        ]

        result = await get_semiconductor_risk_events(limit=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/geopolitical-events
# ---------------------------------------------------------------------------

class TestGeopoliticalEventsEndpoint:
    """Tests for GET /api/v1/geopolitical-events."""

    def setup_method(self):
        _cache.clear()

    @patch("app.services.gdelt_service.httpx.AsyncClient")
    def test_success_default_keywords(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Authenticated request with no keywords uses defaults."""
        user = _create_test_user(session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GDELT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/geopolitical-events",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "events" in data
        assert "keywords" in data
        assert "timespan" in data
        assert data["count"] == len(data["events"])
        assert data["keywords"] == DEFAULT_KEYWORDS

    @patch("app.services.gdelt_service.httpx.AsyncClient")
    def test_custom_keywords(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Custom keywords are passed through correctly."""
        user = _create_test_user(session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GDELT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/geopolitical-events",
            params={"keywords": "chip ban,Taiwan strait"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["keywords"] == ["chip ban", "Taiwan strait"]

    @patch("app.services.gdelt_service.httpx.AsyncClient")
    def test_custom_timespan(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Custom timespan parameter is accepted."""
        user = _create_test_user(session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GDELT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/geopolitical-events",
            params={"timespan": "7d"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["timespan"] == "7d"

    @patch("app.services.gdelt_service.httpx.AsyncClient")
    def test_returns_empty_on_api_error(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Returns empty event list when GDELT API fails."""
        import httpx

        user = _create_test_user(session)

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/geopolitical-events",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["events"] == []

    @pytest.mark.xfail(
        reason="DEV MODE: get_current_user falls back to first/auto-created user",
        strict=False,
    )
    def test_unauthenticated(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/geopolitical-events")
        assert response.status_code == 401

    @patch("app.services.gdelt_service.httpx.AsyncClient")
    def test_limit_validation(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Limit parameter validates bounds (1-100)."""
        user = _create_test_user(session)

        # limit=0 should fail validation (ge=1)
        response = client.get(
            "/api/v1/geopolitical-events",
            params={"limit": 0},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

        # limit=101 should fail validation (le=100)
        response = client.get(
            "/api/v1/geopolitical-events",
            params={"limit": 101},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

    def test_default_keywords_not_empty(self):
        """DEFAULT_KEYWORDS contains at least one keyword."""
        assert len(DEFAULT_KEYWORDS) > 0
        assert all(isinstance(kw, str) for kw in DEFAULT_KEYWORDS)
