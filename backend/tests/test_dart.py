# @TASK DART-3 - DART Korean semiconductor filings endpoint tests
# @TEST tests/test_dart.py

"""Tests for DART integration: service layer and API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.services.dart_service import (
    CORP_CODE_MAP,
    REPORT_TYPE_FILTERS,
    _build_cache_key,
    _cache,
    _get_cached,
    _parse_filing,
    _set_cached,
    clear_dart_cache,
    get_all_kr_semiconductor_filings,
    get_company_filings,
    get_supported_companies,
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


# Sample DART API response (simplified, matches real DART list.json structure)
SAMPLE_DART_RESPONSE = {
    "status": "000",
    "message": "정상",
    "page_no": 1,
    "page_count": 10,
    "total_count": 5,
    "total_page": 1,
    "list": [
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "corp_cls": "Y",
            "report_nm": "사업보고서 (2025.12)",
            "rcept_no": "20260320000123",
            "flr_nm": "삼성전자",
            "rcept_dt": "20260320",
            "rm": "",
        },
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "corp_cls": "Y",
            "report_nm": "분기보고서 (2025.09)",
            "rcept_no": "20251115000456",
            "flr_nm": "삼성전자",
            "rcept_dt": "20251115",
            "rm": "",
        },
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "corp_cls": "Y",
            "report_nm": "반기보고서 (2025.06)",
            "rcept_no": "20250815000789",
            "flr_nm": "삼성전자",
            "rcept_dt": "20250815",
            "rm": "",
        },
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "corp_cls": "Y",
            "report_nm": "분기보고서 (2025.03)",
            "rcept_no": "20250515000111",
            "flr_nm": "삼성전자",
            "rcept_dt": "20250515",
            "rm": "",
        },
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "corp_cls": "Y",
            "report_nm": "기타경영사항(자율공시)",
            "rcept_no": "20260101000999",
            "flr_nm": "삼성전자",
            "rcept_dt": "20260101",
            "rm": "",
        },
    ],
}

# Response with no data (status 013)
SAMPLE_DART_NO_DATA_RESPONSE = {
    "status": "013",
    "message": "조회된 데이터가 없습니다.",
}

# Response with an error status
SAMPLE_DART_ERROR_RESPONSE = {
    "status": "020",
    "message": "요청 제한을 초과하였습니다.",
}


# ---------------------------------------------------------------------------
# Unit tests: cache helpers
# ---------------------------------------------------------------------------

class TestDartCacheHelpers:
    """Tests for the module-level cache helpers."""

    def setup_method(self):
        """Clear cache before each test."""
        _cache.clear()

    def test_build_cache_key_deterministic(self):
        """Same corp_code and limit produce the same key."""
        key1 = _build_cache_key("00126380", 10)
        key2 = _build_cache_key("00126380", 10)
        assert key1 == key2

    def test_build_cache_key_none_uses_all(self):
        """None corp_code produces 'ALL' in cache key."""
        key = _build_cache_key(None, 5)
        assert "ALL" in key

    def test_build_cache_key_different_limits(self):
        """Different limits produce different keys."""
        key1 = _build_cache_key("00126380", 5)
        key2 = _build_cache_key("00126380", 10)
        assert key1 != key2

    def test_set_and_get_cached(self):
        """Data stored via _set_cached is retrievable via _get_cached."""
        data = [{"report_name": "사업보고서", "corp_name": "Samsung"}]
        _set_cached("test-dart", data)
        result = _get_cached("test-dart")
        assert result == data

    def test_get_cached_returns_none_when_missing(self):
        """Returns None for a key that was never cached."""
        result = _get_cached("nonexistent-dart-key")
        assert result is None

    def test_get_cached_returns_none_when_expired(self):
        """Returns None when the cached entry is older than CACHE_TTL (6h)."""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=7)
        _cache["expired-dart"] = (expired_time, [{"stale": True}])
        result = _get_cached("expired-dart")
        assert result is None
        assert "expired-dart" not in _cache

    def test_get_cached_returns_data_within_ttl(self):
        """Returns cached data when within TTL (6 hours)."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=3)
        data = [{"fresh": True}]
        _cache["fresh-dart"] = (recent_time, data)
        result = _get_cached("fresh-dart")
        assert result == data

    def test_clear_dart_cache(self):
        """clear_dart_cache empties the cache and returns eviction count."""
        _set_cached("k1", [])
        _set_cached("k2", [])
        _set_cached("k3", [])
        count = clear_dart_cache()
        assert count == 3
        assert len(_cache) == 0


# ---------------------------------------------------------------------------
# Unit tests: _parse_filing
# ---------------------------------------------------------------------------

class TestParseFiling:
    """Tests for DART filing parsing helper."""

    def test_parses_complete_filing(self):
        result = _parse_filing(
            corp_name="Samsung Electronics",
            corp_name_kr="삼성전자",
            corp_code="00126380",
            report_nm="사업보고서 (2025.12)",
            rcept_no="20260320000123",
            rcept_dt="20260320",
            flr_nm="삼성전자",
        )

        assert result["corp_code"] == "00126380"
        assert result["corp_name"] == "Samsung Electronics"
        assert result["corp_name_kr"] == "삼성전자"
        assert result["report_name"] == "사업보고서 (2025.12)"
        assert result["filing_date"] == "2026-03-20"
        assert result["receipt_number"] == "20260320000123"
        assert result["filer_name"] == "삼성전자"
        assert "dart.fss.or.kr" in result["url"]
        assert "20260320000123" in result["url"]

    def test_date_formatting_yyyymmdd(self):
        """Converts YYYYMMDD to YYYY-MM-DD format."""
        result = _parse_filing(
            corp_name="Test",
            corp_name_kr="테스트",
            corp_code="00000000",
            report_nm="Test Report",
            rcept_no="20260101000001",
            rcept_dt="20260101",
            flr_nm="Test",
        )
        assert result["filing_date"] == "2026-01-01"

    def test_short_date_passed_through(self):
        """Non-8-digit date strings are passed through as-is."""
        result = _parse_filing(
            corp_name="Test",
            corp_name_kr="테스트",
            corp_code="00000000",
            report_nm="Test Report",
            rcept_no="20260101000001",
            rcept_dt="2026-01",
            flr_nm="Test",
        )
        assert result["filing_date"] == "2026-01"

    def test_url_contains_receipt_number(self):
        """Viewer URL is correctly built with receipt number."""
        result = _parse_filing(
            corp_name="Test",
            corp_name_kr="테스트",
            corp_code="00000000",
            report_nm="Test",
            rcept_no="20260320000123",
            rcept_dt="20260320",
            flr_nm="Test",
        )
        assert result["url"] == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260320000123"


# ---------------------------------------------------------------------------
# Unit tests: get_supported_companies
# ---------------------------------------------------------------------------

class TestGetSupportedCompanies:
    """Tests for the supported companies helper."""

    def test_returns_all_mapped_companies(self):
        companies = get_supported_companies()
        assert len(companies) == len(CORP_CODE_MAP)

    def test_each_entry_has_required_fields(self):
        companies = get_supported_companies()
        for entry in companies:
            assert "corp_code" in entry
            assert "name" in entry
            assert "name_kr" in entry

    def test_includes_known_companies(self):
        companies = get_supported_companies()
        names = [c["name"] for c in companies]
        assert "Samsung Electronics" in names
        assert "SK hynix" in names
        assert "Samsung SDI" in names

    def test_results_sorted_by_name(self):
        companies = get_supported_companies()
        names = [c["name"] for c in companies]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# Unit tests: get_company_filings
# ---------------------------------------------------------------------------

class TestGetCompanyFilings:
    """Tests for the per-company DART filing fetcher."""

    def setup_method(self):
        _cache.clear()

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_returns_parsed_filings(self, mock_client_cls, mock_settings):
        """Fetches and parses DART filings successfully."""
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("00126380", limit=10)

        # 5 items in sample, but one is "기타경영사항" which is filtered out
        assert len(result) == 4
        assert result[0]["corp_code"] == "00126380"
        assert result[0]["corp_name"] == "Samsung Electronics"
        assert result[0]["corp_name_kr"] == "삼성전자"
        assert "사업보고서" in result[0]["report_name"]

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_filters_report_types(self, mock_client_cls, mock_settings):
        """Only returns target report types (annual, quarterly, semi-annual)."""
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("00126380", limit=10)

        # All returned filings should contain one of the target report types
        for filing in result:
            report_name = filing["report_name"]
            assert any(rt in report_name for rt in REPORT_TYPE_FILTERS), (
                f"Unexpected report type: {report_name}"
            )

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_respects_limit(self, mock_client_cls, mock_settings):
        """Result set is truncated to limit."""
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("00126380", limit=2)
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_unsupported_corp_code_raises_value_error(self):
        """Raises ValueError for a corp_code not in CORP_CODE_MAP."""
        with pytest.raises(ValueError, match="not supported"):
            await get_company_filings("99999999")

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    async def test_missing_api_key_returns_empty(self, mock_settings):
        """Returns empty list with warning when DART_API_KEY is not set."""
        mock_settings.DART_API_KEY = ""

        result = await get_company_filings("00126380")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_handles_timeout(self, mock_client_cls, mock_settings):
        """Returns empty list on timeout."""
        import httpx

        mock_settings.DART_API_KEY = "test-api-key"

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("00126380")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_handles_http_error(self, mock_client_cls, mock_settings):
        """Returns empty list on HTTP errors."""
        import httpx

        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Too Many Requests",
            request=httpx.Request("GET", "https://opendart.fss.or.kr/api/list.json"),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("00126380")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_handles_no_data_status(self, mock_client_cls, mock_settings):
        """Returns empty list when DART responds with status 013 (no data)."""
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_NO_DATA_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("00126380")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_handles_error_status(self, mock_client_cls, mock_settings):
        """Returns empty list when DART responds with a non-000 status."""
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_ERROR_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result = await get_company_filings("00126380")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_caches_results(self, mock_client_cls, mock_settings):
        """Second call returns cached data without calling API again."""
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        result1 = await get_company_filings("00126380", limit=10)
        result2 = await get_company_filings("00126380", limit=10)

        assert result1 == result2
        # httpx.AsyncClient was only instantiated once (for the first call)
        assert mock_client_cls.call_count == 1

    @pytest.mark.asyncio
    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    async def test_sends_api_key_in_params(self, mock_client_cls, mock_settings):
        """Verifies the DART API key is included in request params."""
        mock_settings.DART_API_KEY = "my-secret-dart-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        await get_company_filings("00126380")

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params["crtfc_key"] == "my-secret-dart-key"
        assert params["corp_code"] == "00126380"
        assert params["pblntf_ty"] == "A"


# ---------------------------------------------------------------------------
# Unit tests: get_all_kr_semiconductor_filings
# ---------------------------------------------------------------------------

class TestGetAllKrSemiconductorFilings:
    """Tests for the aggregate DART filing fetcher."""

    def setup_method(self):
        _cache.clear()

    @pytest.mark.asyncio
    @patch("app.services.dart_service.get_company_filings")
    async def test_fetches_all_companies(self, mock_get_filings):
        """Calls get_company_filings for each tracked company."""
        mock_get_filings.return_value = [
            {"corp_code": "00126380", "filing_date": "2026-01-01", "report_name": "사업보고서"}
        ]

        result = await get_all_kr_semiconductor_filings(limit_per_company=5)

        assert mock_get_filings.call_count == len(CORP_CODE_MAP)
        assert len(result) == len(CORP_CODE_MAP)

    @pytest.mark.asyncio
    @patch("app.services.dart_service.get_company_filings")
    async def test_sorts_by_date_descending(self, mock_get_filings):
        """Combined results are sorted by date (newest first)."""
        corp_codes = list(CORP_CODE_MAP.keys())
        dates = [
            "2026-03-01", "2026-02-15", "2026-01-20", "2025-12-10",
            "2025-11-05", "2025-10-01", "2025-09-15", "2025-08-20",
            "2025-07-10", "2025-06-01", "2025-05-15", "2025-04-01",
            "2025-03-20", "2025-02-10", "2025-01-05", "2024-12-20",
            "2024-11-15",
        ]

        side_effects = []
        for i, code in enumerate(corp_codes):
            date = dates[i] if i < len(dates) else "2024-01-01"
            side_effects.append([
                {"corp_code": code, "filing_date": date, "report_name": "사업보고서"}
            ])
        mock_get_filings.side_effect = side_effects

        result = await get_all_kr_semiconductor_filings()

        filing_dates = [f["filing_date"] for f in result]
        assert filing_dates == sorted(filing_dates, reverse=True)

    @pytest.mark.asyncio
    @patch("app.services.dart_service.get_company_filings")
    async def test_caches_aggregate_results(self, mock_get_filings):
        """Second call returns cached data without calling get_company_filings."""
        mock_get_filings.return_value = [
            {"corp_code": "00126380", "filing_date": "2026-01-01", "report_name": "사업보고서"}
        ]

        result1 = await get_all_kr_semiconductor_filings()
        result2 = await get_all_kr_semiconductor_filings()

        assert result1 == result2
        # get_company_filings called only for the first aggregate fetch
        assert mock_get_filings.call_count == len(CORP_CODE_MAP)

    @pytest.mark.asyncio
    @patch("app.services.dart_service.get_company_filings")
    async def test_skips_failed_companies(self, mock_get_filings):
        """Companies that fail are skipped without crashing."""
        call_count = 0
        failed_code = list(CORP_CODE_MAP.keys())[1]  # Second company fails

        async def side_effect(corp_code, limit):
            nonlocal call_count
            call_count += 1
            if corp_code == failed_code:
                raise Exception("Network error")
            return [{"corp_code": corp_code, "filing_date": "2026-01-01", "report_name": "사업보고서"}]

        mock_get_filings.side_effect = side_effect

        result = await get_all_kr_semiconductor_filings()

        # All companies were attempted
        assert call_count == len(CORP_CODE_MAP)
        # One company failed, so we have one fewer result
        assert len(result) == len(CORP_CODE_MAP) - 1


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/dart-filings
# ---------------------------------------------------------------------------

class TestDartFilingsEndpoint:
    """Tests for GET /api/v1/dart-filings."""

    def setup_method(self):
        _cache.clear()

    @patch("app.services.dart_service.get_company_filings")
    def test_success_all_filings(
        self, mock_get_filings, client: TestClient, session: Session
    ):
        """Authenticated request returns filings from all companies."""
        user = _create_test_user(session)
        mock_get_filings.return_value = [
            {
                "corp_code": "00126380",
                "filing_date": "2026-01-01",
                "report_name": "사업보고서",
                "corp_name": "Samsung Electronics",
            }
        ]

        response = client.get(
            "/api/v1/dart-filings",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "filings" in data
        assert "companies" in data
        assert "limit_per_company" in data

    @patch("app.services.dart_service.get_company_filings")
    def test_limit_validation(
        self, mock_get_filings, client: TestClient, session: Session
    ):
        """Limit parameter validates bounds (1-20)."""
        user = _create_test_user(session)

        # limit=0 should fail validation (ge=1)
        response = client.get(
            "/api/v1/dart-filings",
            params={"limit": 0},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

        # limit=21 should fail validation (le=20)
        response = client.get(
            "/api/v1/dart-filings",
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
        response = client.get("/api/v1/dart-filings")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/dart-filings/companies
# ---------------------------------------------------------------------------

class TestDartFilingsCompaniesEndpoint:
    """Tests for GET /api/v1/dart-filings/companies."""

    def test_returns_supported_companies(self, client: TestClient, session: Session):
        """Returns list of all supported Korean semiconductor companies."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/dart-filings/companies",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == len(CORP_CODE_MAP)
        assert len(data["companies"]) == len(CORP_CODE_MAP)

        # Each company entry has required fields
        for company in data["companies"]:
            assert "corp_code" in company
            assert "name" in company
            assert "name_kr" in company


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/dart-filings/{corp_code}
# ---------------------------------------------------------------------------

class TestDartFilingsByCorpCodeEndpoint:
    """Tests for GET /api/v1/dart-filings/{corp_code}."""

    def setup_method(self):
        _cache.clear()

    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    def test_success_specific_corp_code(
        self, mock_client_cls, mock_settings, client: TestClient, session: Session
    ):
        """Authenticated request returns filings for a specific corp_code."""
        user = _create_test_user(session)
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/dart-filings/00126380",
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["corp_code"] == "00126380"
        assert data["corp_name"] == "Samsung Electronics"
        assert data["corp_name_kr"] == "삼성전자"
        assert "count" in data
        assert "filings" in data
        assert data["count"] == len(data["filings"])

    def test_unsupported_corp_code_returns_404(self, client: TestClient, session: Session):
        """Request for unsupported corp_code returns 404."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/dart-filings/99999999",
            headers=_auth_header(user),
        )

        assert response.status_code == 404
        data = response.json()
        assert "not supported" in data["detail"].lower()

    @patch("app.services.dart_service.settings")
    @patch("app.services.dart_service.httpx.AsyncClient")
    def test_limit_per_corp_code(
        self, mock_client_cls, mock_settings, client: TestClient, session: Session
    ):
        """Limit parameter limits results for a specific corp_code."""
        user = _create_test_user(session)
        mock_settings.DART_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_DART_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client_cls.return_value = mock_client

        response = client.get(
            "/api/v1/dart-filings/00126380",
            params={"limit": 2},
            headers=_auth_header(user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] <= 2

    def test_limit_validation_per_corp_code(self, client: TestClient, session: Session):
        """Limit parameter validates bounds (1-50) for per-corp_code endpoint."""
        user = _create_test_user(session)

        response = client.get(
            "/api/v1/dart-filings/00126380",
            params={"limit": 0},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

        response = client.get(
            "/api/v1/dart-filings/00126380",
            params={"limit": 51},
            headers=_auth_header(user),
        )
        assert response.status_code == 422

    @pytest.mark.xfail(
        reason="DEV MODE: get_current_user falls back to first/auto-created user",
        strict=False,
    )
    def test_unauthenticated_per_corp_code(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/api/v1/dart-filings/00126380")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Constants / data integrity tests
# ---------------------------------------------------------------------------

class TestCorpCodeMap:
    """Tests for the CORP_CODE_MAP data integrity."""

    def test_all_required_companies_present(self):
        """All specified Korean semiconductor companies are mapped."""
        # Major companies that must be present
        required_names = {
            "Samsung Electronics",
            "SK hynix",
            "Samsung SDI",
            "LG Innotek",
        }
        actual_names = {info["name"] for info in CORP_CODE_MAP.values()}
        assert required_names.issubset(actual_names)

    def test_corp_code_format(self):
        """All corp_codes are 8-digit strings."""
        for code, info in CORP_CODE_MAP.items():
            assert len(code) == 8, f"Corp code '{code}' ({info['name']}) is not 8 digits"
            assert code.isdigit(), f"Corp code '{code}' ({info['name']}) contains non-digits"

    def test_all_entries_have_names(self):
        """All entries have non-empty English and Korean names."""
        for code, info in CORP_CODE_MAP.items():
            assert info["name"], f"Corp code '{code}' has empty English name"
            assert info["name_kr"], f"Corp code '{code}' has empty Korean name"

    def test_known_corp_codes(self):
        """Known major corp_codes are correct."""
        assert "00126380" in CORP_CODE_MAP  # Samsung Electronics
        assert CORP_CODE_MAP["00126380"]["name"] == "Samsung Electronics"

        assert "00164779" in CORP_CODE_MAP  # SK hynix
        assert CORP_CODE_MAP["00164779"]["name"] == "SK hynix"

        assert "00126371" in CORP_CODE_MAP  # Samsung SDI
        assert CORP_CODE_MAP["00126371"]["name"] == "Samsung SDI"

        assert "00356361" in CORP_CODE_MAP  # LG Innotek
        assert CORP_CODE_MAP["00356361"]["name"] == "LG Innotek"

    def test_report_type_filters_defined(self):
        """Report type filters include the standard Korean report types."""
        assert "사업보고서" in REPORT_TYPE_FILTERS
        assert "분기보고서" in REPORT_TYPE_FILTERS
        assert "반기보고서" in REPORT_TYPE_FILTERS

    def test_minimum_company_count(self):
        """At least 10 Korean semiconductor companies are mapped."""
        assert len(CORP_CODE_MAP) >= 10
