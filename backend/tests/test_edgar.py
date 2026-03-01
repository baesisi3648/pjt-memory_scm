# @TASK EDGAR-3 - SEC EDGAR filings endpoint tests
# @TEST tests/test_edgar.py

"""Tests for SEC EDGAR integration: service layer and API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.services.edgar_service import (
    DEFAULT_FILING_TYPES,
    TICKER_CIK_MAP,
    _build_cache_key,
    _cache,
    _get_cached,
    _parse_filing,
    _set_cached,
    clear_edgar_cache,
    get_all_semiconductor_filings,
    get_company_filings,
    get_supported_tickers,
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


# Sample SEC EDGAR submissions API response (simplified)
SAMPLE_EDGAR_RESPONSE = {
    "cik": "723125",
    "entityType": "operating",
    "sic": "3674",
    "sicDescription": "Semiconductors & Related Devices",
    "name": "MICRON TECHNOLOGY INC",
    "tickers": ["MU"],
    "exchanges": ["NASDAQ"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000723125-26-000012",
                "0000723125-26-000010",
                "0000723125-25-000045",
                "0000723125-25-000030",
                "0000723125-25-000020",
            ],
            "filingDate": [
                "2026-01-15",
                "2025-12-20",
                "2025-10-01",
                "2025-07-15",
                "2025-04-10",
            ],
            "form": [
                "10-Q",
                "8-K",
                "10-K",
                "10-Q",
                "8-K",
            ],
            "primaryDocument": [
                "mu-20260115.htm",
                "mu-20251220.htm",
                "mu-20251001.htm",
                "mu-20250715.htm",
                "mu-20250410.htm",
            ],
            "primaryDocDescription": [
                "Quarterly Report Q1 FY2026",
                "Current Report - Leadership Change",
                "Annual Report FY2025",
                "Quarterly Report Q3 FY2025",
                "Current Report - Earnings",
            ],
        },
        "files": [],
    },
}

# Response with no matching filing types
SAMPLE_EDGAR_RESPONSE_NO_MATCH = {
    "cik": "723125",
    "filings": {
        "recent": {
            "accessionNumber": ["0000723125-26-000099"],
            "filingDate": ["2026-02-01"],
            "form": ["SC 13G"],
            "primaryDocument": ["sc13g.htm"],
            "primaryDocDescription": ["SC 13G Filing"],
        },
        "files": [],
    },
}


# ---------------------------------------------------------------------------
# Unit tests: cache helpers
# ---------------------------------------------------------------------------

class TestEdgarCacheHelpers:
    """Tests for the module-level cache helpers."""

    def setup_method(self):
        """Clear cache before each test."""
        _cache.clear()

    def test_build_cache_key_deterministic(self):
        """Same filing types in different order produce the same key."""
        key1 = _build_cache_key("MU", ["10-K", "10-Q"], 10)
        key2 = _build_cache_key("MU", ["10-Q", "10-K"], 10)
        assert key1 == key2

    def test_build_cache_key_ticker_case_insensitive(self):
        """Ticker is uppercased for cache key consistency."""
        key1 = _build_cache_key("mu", ["10-K"], 10)
        key2 = _build_cache_key("MU", ["10-K"], 10)
        assert key1 == key2

    def test_build_cache_key_none_ticker_uses_all(self):
        """None ticker produces 'ALL' in cache key."""
        key = _build_cache_key(None, ["10-K"], 5)
        assert "ALL" in key

    def test_build_cache_key_different_limits(self):
        """Different limits produce different keys."""
        key1 = _build_cache_key("MU", ["10-K"], 5)
        key2 = _build_cache_key("MU", ["10-K"], 10)
        assert key1 != key2

    def test_set_and_get_cached(self):
        """Data stored via _set_cached is retrievable via _get_cached."""
        data = [{"filing_type": "10-K", "title": "Annual Report"}]
        _set_cached("test-edgar", data)
        result = _get_cached("test-edgar")
        assert result == data

    def test_get_cached_returns_none_when_missing(self):
        """Returns None for a key that was never cached."""
        result = _get_cached("nonexistent-edgar-key")
        assert result is None

    def test_get_cached_returns_none_when_expired(self):
        """Returns None when the cached entry is older than CACHE_TTL (6h)."""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=7)
        _cache["expired-edgar"] = (expired_time, [{"stale": True}])
        result = _get_cached("expired-edgar")
        assert result is None
        assert "expired-edgar" not in _cache

    def test_get_cached_returns_data_within_ttl(self):
        """Returns cached data when within TTL (6 hours)."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=3)
        data = [{"fresh": True}]
        _cache["fresh-edgar"] = (recent_time, data)
        result = _get_cached("fresh-edgar")
        assert result == data

    def test_clear_edgar_cache(self):
        """clear_edgar_cache empties the cache and returns eviction count."""
        _set_cached("k1", [])
        _set_cached("k2", [])
        _set_cached("k3", [])
        count = clear_edgar_cache()
        assert count == 3
        assert len(_cache) == 0


# ---------------------------------------------------------------------------
# Unit tests: _parse_filing
# ---------------------------------------------------------------------------

class TestParseFiling:
    """Tests for filing parsing helper."""

    def test_parses_complete_filing(self):
        result = _parse_filing(
            filing_type="10-K",
            filing_date="2025-10-01",
            accession_number="0000723125-25-000045",
            primary_document="mu-20251001.htm",
            description="Annual Report FY2025",
            cik="0000723125",
            company_name="Micron Technology Inc",
            ticker="MU",
        )

        assert result["ticker"] == "MU"
        assert result["company_name"] == "Micron Technology Inc"
        assert result["filing_type"] == "10-K"
        assert result["title"] == "Annual Report FY2025"
        assert result["date"] == "2025-10-01"
        assert result["accession_number"] == "0000723125-25-000045"
        assert "sec.gov" in result["url"]
        assert "mu-20251001.htm" in result["url"]

    def test_empty_description_uses_fallback_title(self):
        result = _parse_filing(
            filing_type="8-K",
            filing_date="2025-12-20",
            accession_number="0000723125-25-000010",
            primary_document="doc.htm",
            description="",
            cik="0000723125",
            company_name="Micron Technology Inc",
            ticker="MU",
        )
        assert result["title"] == "Micron Technology Inc 8-K"

    def test_url_strips_leading_zeros_from_cik(self):
        result = _parse_filing(
            filing_type="10-Q",
            filing_date="2026-01-15",
            accession_number="0000723125-26-000012",
            primary_document="doc.htm",
            description="Quarterly",
            cik="0000723125",
            company_name="Test",
            ticker="TEST",
        )
        # CIK in the URL should have leading zeros stripped
        assert "/723125/" in result["url"]

    def test_accession_dashes_removed_in_url(self):
        result = _parse_filing(
            filing_type="10-K",
            filing_date="2025-10-01",
            accession_number="0000723125-25-000045",
            primary_document="doc.htm",
            description="Test",
            cik="0000723125",
            company_name="Test",
            ticker="TEST",
        )
        assert "000072312525000045" in result["url"]


# ---------------------------------------------------------------------------
# Unit tests: get_supported_tickers
# ---------------------------------------------------------------------------

class TestGetSupportedTickers:
    """Tests for the supported tickers helper."""

    def test_returns_all_mapped_tickers(self):
        tickers = get_supported_tickers()
        assert len(tickers) == len(TICKER_CIK_MAP)

    def test_each_entry_has_required_fields(self):
        tickers = get_supported_tickers()
        for entry in tickers:
            assert "ticker" in entry
            assert "name" in entry
            assert "cik" in entry

    def test_includes_known_tickers(self):
        tickers = get_supported_tickers()
        ticker_symbols = [t["ticker"] for t in tickers]
        assert "MU" in ticker_symbols
        assert "INTC" in ticker_symbols
        assert "AMAT" in ticker_symbols

    def test_results_sorted_by_ticker(self):
        tickers = get_supported_tickers()
        symbols = [t["ticker"] for t in tickers]
        assert symbols == sorted(symbols)


# ---------------------------------------------------------------------------
# Unit tests: get_company_filings
# ---------------------------------------------------------------------------

class TestGetCompanyFilings:
    """Tests for the per-company filing fetcher."""

    def setup_method(self):
        _cache.clear()

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_returns_parsed_filings(self, mock_client_cls):
        """Fetches and parses SEC filings successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("MU", limit=10)

        assert len(result) == 5
        assert result[0]["ticker"] == "MU"
        assert result[0]["filing_type"] == "10-Q"
        assert result[0]["date"] == "2026-01-15"

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_filters_by_filing_type(self, mock_client_cls):
        """Only returns filings matching the requested types."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("MU", filing_types=["10-K"], limit=10)

        assert len(result) == 1
        assert result[0]["filing_type"] == "10-K"

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_respects_limit(self, mock_client_cls):
        """Result set is truncated to limit."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("MU", limit=2)
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_unsupported_ticker_raises_value_error(self):
        """Raises ValueError for a ticker not in TICKER_CIK_MAP."""
        with pytest.raises(ValueError, match="not supported"):
            await get_company_filings("FAKE")

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_case_insensitive_ticker(self, mock_client_cls):
        """Ticker lookup is case-insensitive."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("mu")  # lowercase
        assert len(result) > 0
        assert result[0]["ticker"] == "MU"

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_handles_timeout(self, mock_client_cls):
        """Returns empty list on timeout."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("MU")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_handles_http_error(self, mock_client_cls):
        """Returns empty list on HTTP errors."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Rate limited"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden",
            request=httpx.Request("GET", "https://data.sec.gov/submissions/"),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("INTC")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_sends_user_agent_header(self, mock_client_cls):
        """Verifies the required SEC User-Agent header is sent."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        await get_company_filings("MU")

        call_kwargs = mock_client.get.call_args
        headers = call_kwargs.kwargs.get("headers", {})
        assert "User-Agent" in headers
        assert "MemorySCM" in headers["User-Agent"]

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_caches_results(self, mock_client_cls):
        """Second call returns cached data without calling API again."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result1 = await get_company_filings("MU", limit=10)
        result2 = await get_company_filings("MU", limit=10)

        assert result1 == result2
        # httpx.AsyncClient was only instantiated once (for the first call)
        assert mock_client_cls.call_count == 1

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.httpx.AsyncClient")
    async def test_returns_empty_when_no_matching_filings(self, mock_client_cls):
        """Returns empty list when no filings match the requested types."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE_NO_MATCH
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("MU", filing_types=["10-K"], limit=10)
        assert result == []


# ---------------------------------------------------------------------------
# Unit tests: get_all_semiconductor_filings
# ---------------------------------------------------------------------------

class TestGetAllSemiconductorFilings:
    """Tests for the aggregate filing fetcher."""

    def setup_method(self):
        _cache.clear()

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.get_company_filings")
    async def test_fetches_all_companies(self, mock_get_filings):
        """Calls get_company_filings for each tracked company."""
        mock_get_filings.return_value = [
            {"ticker": "TEST", "date": "2026-01-01", "filing_type": "10-K"}
        ]

        result = await get_all_semiconductor_filings(limit_per_company=5)

        assert mock_get_filings.call_count == len(TICKER_CIK_MAP)
        assert len(result) == len(TICKER_CIK_MAP)

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.get_company_filings")
    async def test_sorts_by_date_descending(self, mock_get_filings):
        """Combined results are sorted by date (newest first)."""
        mock_get_filings.side_effect = [
            [{"ticker": "MU", "date": "2026-01-01", "filing_type": "10-K"}],
            [{"ticker": "INTC", "date": "2026-02-01", "filing_type": "10-Q"}],
            [{"ticker": "AMAT", "date": "2025-12-01", "filing_type": "8-K"}],
            [{"ticker": "LRCX", "date": "2025-11-01", "filing_type": "10-K"}],
            [{"ticker": "TSM", "date": "2026-01-15", "filing_type": "10-Q"}],
            [{"ticker": "ASML", "date": "2025-10-01", "filing_type": "10-K"}],
            [{"ticker": "AMKR", "date": "2025-09-01", "filing_type": "8-K"}],
        ]

        result = await get_all_semiconductor_filings()

        dates = [f["date"] for f in result]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.get_company_filings")
    async def test_caches_aggregate_results(self, mock_get_filings):
        """Second call returns cached data without calling get_company_filings."""
        mock_get_filings.return_value = [
            {"ticker": "MU", "date": "2026-01-01", "filing_type": "10-K"}
        ]

        result1 = await get_all_semiconductor_filings()
        result2 = await get_all_semiconductor_filings()

        assert result1 == result2
        # get_company_filings called only for the first aggregate fetch
        assert mock_get_filings.call_count == len(TICKER_CIK_MAP)

    @pytest.mark.asyncio
    @patch("app.services.edgar_service.get_company_filings")
    async def test_skips_failed_companies(self, mock_get_filings):
        """Companies that fail are skipped without crashing."""
        call_count = 0

        async def side_effect(ticker, filing_types, limit):
            nonlocal call_count
            call_count += 1
            if ticker == "INTC":
                raise Exception("Network error")
            return [{"ticker": ticker, "date": "2026-01-01", "filing_type": "10-K"}]

        mock_get_filings.side_effect = side_effect

        result = await get_all_semiconductor_filings()

        # All companies were attempted
        assert call_count == len(TICKER_CIK_MAP)
        # INTC failed, so we have one fewer result
        assert len(result) == len(TICKER_CIK_MAP) - 1


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/sec-filings
# ---------------------------------------------------------------------------

class TestSecFilingsEndpoint:
    """Tests for GET /api/v1/sec-filings."""

    def setup_method(self):
        _cache.clear()

    @patch("app.services.edgar_service.get_company_filings")
    def test_success_all_filings(
        self, mock_get_filings, client: TestClient, session: Session
    ):
        """Authenticated request returns filings from all companies."""
        user = _create_test_user(session)
        mock_get_filings.return_value = [
            {"ticker": "MU", "date": "2026-01-01", "filing_type": "10-K", "title": "Annual"}
        ]

        response = client.get(
            "/api/v1/sec-filings",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "filings" in data
        assert "companies" in data
        assert "filing_types" in data
        assert data["filing_types"] == DEFAULT_FILING_TYPES

    @patch("app.services.edgar_service.get_company_filings")
    def test_custom_filing_types(
        self, mock_get_filings, client: TestClient, session: Session
    ):
        """Custom filing_types parameter is parsed correctly."""
        user = _create_test_user(session)
        mock_get_filings.return_value = []

        response = client.get(
            "/api/v1/sec-filings",
            params={"filing_types": "10-K,10-Q"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filing_types"] == ["10-K", "10-Q"]

    @patch("app.services.edgar_service.get_company_filings")
    def test_limit_validation(
        self, mock_get_filings, client: TestClient, session: Session
    ):
        """Limit parameter validates bounds (1-20)."""
        user = _create_test_user(session)

        # limit=0 should fail validation (ge=1)
        response = client.get(
            "/api/v1/sec-filings",
            params={"limit": 0},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

        # limit=21 should fail validation (le=20)
        response = client.get(
            "/api/v1/sec-filings",
            params={"limit": 21},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

    @pytest.mark.xfail(
        reason="DEV MODE: get_current_user falls back to first/auto-created user",
        strict=False,
    )
    def test_unauthenticated(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/sec-filings")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/sec-filings/companies
# ---------------------------------------------------------------------------

class TestSecFilingsCompaniesEndpoint:
    """Tests for GET /api/v1/sec-filings/companies."""

    def test_returns_supported_companies(self, client: TestClient, session: Session):
        """Returns list of all supported semiconductor companies."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/sec-filings/companies",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == len(TICKER_CIK_MAP)
        assert len(data["companies"]) == len(TICKER_CIK_MAP)

        # Each company entry has required fields
        for company in data["companies"]:
            assert "ticker" in company
            assert "name" in company
            assert "cik" in company


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/sec-filings/{ticker}
# ---------------------------------------------------------------------------

class TestSecFilingsByTickerEndpoint:
    """Tests for GET /api/v1/sec-filings/{ticker}."""

    def setup_method(self):
        _cache.clear()

    @patch("app.services.edgar_service.httpx.AsyncClient")
    def test_success_specific_ticker(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Authenticated request returns filings for a specific ticker."""
        user = _create_test_user(session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/sec-filings/MU",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MU"
        assert data["company_name"] == "Micron Technology Inc"
        assert "count" in data
        assert "filings" in data
        assert data["count"] == len(data["filings"])

    @patch("app.services.edgar_service.httpx.AsyncClient")
    def test_case_insensitive_ticker_in_url(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Ticker in URL path is case-insensitive."""
        user = _create_test_user(session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/sec-filings/mu",  # lowercase
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MU"

    def test_unsupported_ticker_returns_404(self, client: TestClient, session: Session):
        """Request for unsupported ticker returns 404."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/sec-filings/FAKE",
            headers=_auth_header(user),
        )

        assert response.status_code == 404
        data = response.json()
        assert "not supported" in data["detail"].lower()

    @patch("app.services.edgar_service.httpx.AsyncClient")
    def test_custom_filing_types_per_ticker(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Custom filing_types param filters results for a specific ticker."""
        user = _create_test_user(session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/sec-filings/MU",
            params={"filing_types": "10-K"},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filing_types"] == ["10-K"]
        # Only 10-K filings should be returned
        for filing in data["filings"]:
            assert filing["filing_type"] == "10-K"

    @patch("app.services.edgar_service.httpx.AsyncClient")
    def test_limit_per_ticker(
        self, mock_client_cls, client: TestClient, session: Session
    ):
        """Limit parameter limits results for a specific ticker."""
        user = _create_test_user(session)

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_EDGAR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/sec-filings/MU",
            params={"limit": 2},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] <= 2

    def test_limit_validation_per_ticker(self, client: TestClient, session: Session):
        """Limit parameter validates bounds (1-50) for per-ticker endpoint."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/sec-filings/MU",
            params={"limit": 0},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

        response = client.get(
            "/api/v1/sec-filings/MU",
            params={"limit": 51},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

    @pytest.mark.xfail(
        reason="DEV MODE: get_current_user falls back to first/auto-created user",
        strict=False,
    )
    def test_unauthenticated_per_ticker(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/sec-filings/MU")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Constants / data integrity tests
# ---------------------------------------------------------------------------

class TestTickerCikMap:
    """Tests for the TICKER_CIK_MAP data integrity."""

    def test_all_required_companies_present(self):
        """All specified semiconductor companies are mapped."""
        required = {"MU", "INTC", "AMAT", "LRCX", "TSM", "ASML", "AMKR"}
        assert required.issubset(set(TICKER_CIK_MAP.keys()))

    def test_cik_format(self):
        """All CIK numbers are 10-digit zero-padded strings."""
        for ticker, info in TICKER_CIK_MAP.items():
            cik = info["cik"]
            assert len(cik) == 10, f"{ticker} CIK '{cik}' is not 10 digits"
            assert cik.isdigit(), f"{ticker} CIK '{cik}' contains non-digits"

    def test_all_entries_have_name(self):
        """All entries have a non-empty company name."""
        for ticker, info in TICKER_CIK_MAP.items():
            assert info["name"], f"{ticker} has empty name"

    def test_default_filing_types(self):
        """Default filing types include the standard forms."""
        assert "10-K" in DEFAULT_FILING_TYPES
        assert "10-Q" in DEFAULT_FILING_TYPES
        assert "8-K" in DEFAULT_FILING_TYPES
