# @TASK DART-1 - DART (Financial Supervisory Service) integration for Korean semiconductor filings
# @SPEC DART Open API: https://opendart.fss.or.kr/guide/main.do

"""DART (Korea FSS) electronic disclosure integration service.

Fetches public company filings from the Korean Financial Supervisory Service's
DART system for Korean semiconductor companies tracked by Memory SCM.

DART API requires an API key (crtfc_key) on every request. The key is stored
in settings.DART_API_KEY and loaded from the .env file.

Rate limit: We self-impose a 200ms delay between requests to be polite.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# DART API base URL
DART_API_BASE = "https://opendart.fss.or.kr/api/"

# DART filing list endpoint
DART_LIST_URL = f"{DART_API_BASE}list.json"

# DART filing viewer base URL
DART_VIEWER_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt_number}"

# Filing type codes for DART pblntf_ty parameter:
#   A = Regular filings (annual/quarterly/semi-annual reports)
#   B = Major disclosures
#   C = Issue disclosures
#   D = Ownership disclosures
#   E = Other disclosures
#   F = External audit
#   G = Fund disclosures
#   H = Governance disclosures
#   I = Other
DEFAULT_PBLNTF_TY = "A"

# Report types we care about (Korean names)
# These appear in report_nm field from DART API response
REPORT_TYPE_FILTERS = [
    "사업보고서",     # Annual business report
    "분기보고서",     # Quarterly report
    "반기보고서",     # Semi-annual report
]

# Hardcoded corp_code mapping for major Korean semiconductor companies.
# These are DART-specific 8-digit corporation codes, looked up from DART.
# Using hardcoded values for reliability (avoids runtime search API dependency).
CORP_CODE_MAP: dict[str, dict] = {
    "00126380": {
        "name": "Samsung Electronics",
        "name_kr": "삼성전자",
    },
    "00164779": {
        "name": "SK hynix",
        "name_kr": "SK하이닉스",
    },
    "00126371": {
        "name": "Samsung SDI",
        "name_kr": "삼성SDI",
    },
    "00356361": {
        "name": "LG Innotek",
        "name_kr": "LG이노텍",
    },
    "00631518": {
        "name": "SK Materials",
        "name_kr": "SK머티리얼즈",
    },
    "00577498": {
        "name": "SK Nexilis",
        "name_kr": "SK넥실리스",
    },
    "00466252": {
        "name": "Soulbrain",
        "name_kr": "솔브레인",
    },
    "00214543": {
        "name": "NEPES",
        "name_kr": "네페스",
    },
    "00254741": {
        "name": "Hana Micron",
        "name_kr": "하나마이크론",
    },
    "00155616": {
        "name": "Daeduck Electronics",
        "name_kr": "대덕전자",
    },
    "00359532": {
        "name": "DNF",
        "name_kr": "디엔에프",
    },
    "00119043": {
        "name": "Hansol Chemical",
        "name_kr": "한솔케미칼",
    },
    "00781607": {
        "name": "SEMES",
        "name_kr": "세메스",
    },
    "00550498": {
        "name": "PSK",
        "name_kr": "피에스케이",
    },
    "00286963": {
        "name": "SFA Semicon",
        "name_kr": "에스에프에이반도체",
    },
    "00557540": {
        "name": "BH",
        "name_kr": "비에이치",
    },
    "00551091": {
        "name": "Innox",
        "name_kr": "이녹스",
    },
}

# Module-level cache: key -> (timestamp, data)
_cache: dict[str, tuple[datetime, list[dict]]] = {}
CACHE_TTL = timedelta(hours=6)

# Rate-limiting: track last request time to enforce 200ms between requests
_last_request_time: float = 0.0
_REQUEST_INTERVAL: float = 0.2  # 200ms delay between requests


def _build_cache_key(corp_code: str | None, limit: int) -> str:
    """Build a deterministic cache key."""
    code_part = corp_code if corp_code else "ALL"
    return f"dart:{code_part}:{limit}"


def _get_cached(key: str) -> list[dict] | None:
    """Return cached data if present and not expired, otherwise None."""
    if key in _cache:
        cached_time, cached_data = _cache[key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            logger.debug("Cache hit for DART key: %s", key)
            return cached_data
        del _cache[key]
    return None


def _set_cached(key: str, data: list[dict]) -> None:
    """Store data in the module-level cache."""
    _cache[key] = (datetime.now(timezone.utc), data)


async def _rate_limit_wait() -> None:
    """Wait if necessary to enforce 200ms delay between DART API requests."""
    global _last_request_time

    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _REQUEST_INTERVAL:
        await asyncio.sleep(_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _parse_filing(
    corp_name: str,
    corp_name_kr: str,
    corp_code: str,
    report_nm: str,
    rcept_no: str,
    rcept_dt: str,
    flr_nm: str,
) -> dict:
    """Parse a single DART filing into a structured dict.

    Args:
        corp_name: English company name.
        corp_name_kr: Korean company name.
        corp_code: DART corporation code.
        report_nm: Report name from DART (Korean).
        rcept_no: Receipt number (used to build viewer URL).
        rcept_dt: Receipt date in YYYYMMDD format.
        flr_nm: Filer name.

    Returns:
        Structured dict with filing metadata and URL.
    """
    # Format date from YYYYMMDD to YYYY-MM-DD
    filing_date = rcept_dt
    if len(rcept_dt) == 8:
        filing_date = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}"

    viewer_url = DART_VIEWER_URL.format(receipt_number=rcept_no)

    return {
        "corp_code": corp_code,
        "corp_name": corp_name,
        "corp_name_kr": corp_name_kr,
        "report_name": report_nm,
        "filing_date": filing_date,
        "receipt_number": rcept_no,
        "filer_name": flr_nm,
        "url": viewer_url,
    }


async def get_company_filings(
    corp_code: str,
    limit: int = 10,
) -> list[dict]:
    """Fetch recent DART filings for a specific Korean company.

    Uses the DART list.json API to retrieve filing metadata for regular
    disclosures (annual, quarterly, semi-annual reports).

    Args:
        corp_code: DART 8-digit corporation code (e.g. "00126380").
        limit: Maximum number of filings to return.

    Returns:
        List of filing dicts with: corp_code, corp_name, corp_name_kr,
        report_name, filing_date, receipt_number, filer_name, url.

    Raises:
        ValueError: If the corp_code is not in the supported company map.
    """
    if corp_code not in CORP_CODE_MAP:
        supported = ", ".join(sorted(CORP_CODE_MAP.keys()))
        raise ValueError(
            f"Corporation code '{corp_code}' is not supported. "
            f"Supported codes: {supported}"
        )

    api_key = settings.DART_API_KEY
    if not api_key:
        logger.warning(
            "DART_API_KEY is not configured. "
            "Set DART_API_KEY in .env to enable Korean filing data."
        )
        return []

    company_info = CORP_CODE_MAP[corp_code]
    corp_name = company_info["name"]
    corp_name_kr = company_info["name_kr"]

    # Check cache first
    cache_key = _build_cache_key(corp_code, limit)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # Fetch from DART API - get recent regular filings
    # bgn_de = start date (1 year ago), end_de = today
    now = datetime.now(timezone.utc)
    bgn_de = (now - timedelta(days=365)).strftime("%Y%m%d")
    end_de = now.strftime("%Y%m%d")

    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "pblntf_ty": DEFAULT_PBLNTF_TY,
        "page_count": str(min(limit * 3, 100)),  # Fetch extra to filter
        "page_no": "1",
    }

    try:
        await _rate_limit_wait()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                DART_LIST_URL,
                params=params,
                headers={"Accept": "application/json; charset=utf-8"},
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        logger.warning(
            "DART API request timed out for corp_code=%s (%s)",
            corp_code,
            corp_name,
        )
        return []
    except httpx.HTTPStatusError as exc:
        logger.error(
            "DART API returned HTTP %d for corp_code=%s: %s",
            exc.response.status_code,
            corp_code,
            exc.response.text[:200],
        )
        return []
    except httpx.HTTPError as exc:
        logger.error(
            "Network error calling DART API for corp_code=%s: %s",
            corp_code,
            exc,
        )
        return []
    except (ValueError, KeyError) as exc:
        logger.error(
            "Failed to parse DART API response for corp_code=%s: %s",
            corp_code,
            exc,
        )
        return []

    # DART API response structure:
    # {
    #   "status": "000",  # 000=success, 013=no data
    #   "message": "정상",
    #   "page_no": 1,
    #   "page_count": 10,
    #   "total_count": 42,
    #   "total_page": 5,
    #   "list": [
    #     {
    #       "corp_code": "00126380",
    #       "corp_name": "삼성전자",
    #       "stock_code": "005930",
    #       "corp_cls": "Y",
    #       "report_nm": "사업보고서 (2024.12)",
    #       "rcept_no": "20250320000123",
    #       "flr_nm": "삼성전자",
    #       "rcept_dt": "20250320",
    #       "rm": ""
    #     }, ...
    #   ]
    # }

    status_code = data.get("status", "")
    if status_code == "013":
        # No data found - this is normal, not an error
        logger.info(
            "No DART filings found for corp_code=%s (%s)",
            corp_code,
            corp_name,
        )
        return []
    elif status_code != "000":
        logger.warning(
            "DART API returned status=%s message=%s for corp_code=%s",
            status_code,
            data.get("message", "unknown"),
            corp_code,
        )
        return []

    filing_list = data.get("list", [])
    if not filing_list:
        logger.info(
            "Empty filing list from DART for corp_code=%s (%s)",
            corp_code,
            corp_name,
        )
        return []

    # Filter to only reports we care about (annual, quarterly, semi-annual)
    filings: list[dict] = []
    for item in filing_list:
        report_nm = item.get("report_nm", "")

        # Check if the report name matches any of our target types
        is_target_report = any(
            rt in report_nm for rt in REPORT_TYPE_FILTERS
        )
        if not is_target_report:
            continue

        filings.append(
            _parse_filing(
                corp_name=corp_name,
                corp_name_kr=corp_name_kr,
                corp_code=corp_code,
                report_nm=report_nm,
                rcept_no=item.get("rcept_no", ""),
                rcept_dt=item.get("rcept_dt", ""),
                flr_nm=item.get("flr_nm", ""),
            )
        )

        if len(filings) >= limit:
            break

    logger.info(
        "Fetched %d filings for %s (%s) from DART",
        len(filings),
        corp_code,
        corp_name,
    )

    _set_cached(cache_key, filings)
    return filings


async def get_all_kr_semiconductor_filings(
    limit_per_company: int = 5,
) -> list[dict]:
    """Fetch recent filings for all tracked Korean semiconductor companies.

    Iterates through the CORP_CODE_MAP and fetches filings for each company.
    Results are cached for 6 hours at the aggregate level.

    Args:
        limit_per_company: Maximum filings per company.

    Returns:
        Combined list of filing dicts from all companies, sorted by
        filing_date descending (newest first).
    """
    # Check aggregate cache
    cache_key = _build_cache_key(None, limit_per_company)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    all_filings: list[dict] = []

    for corp_code in CORP_CODE_MAP:
        try:
            company_filings = await get_company_filings(
                corp_code=corp_code,
                limit=limit_per_company,
            )
            all_filings.extend(company_filings)
        except Exception:
            logger.exception(
                "Failed to fetch DART filings for %s, skipping",
                corp_code,
            )
            continue

    # Sort all filings by date descending (newest first)
    all_filings.sort(key=lambda f: f.get("filing_date", ""), reverse=True)

    logger.info(
        "Fetched %d total DART filings across %d Korean semiconductor companies",
        len(all_filings),
        len(CORP_CODE_MAP),
    )

    _set_cached(cache_key, all_filings)
    return all_filings


def get_supported_companies() -> list[dict]:
    """Return the list of supported Korean companies and their corp codes.

    Returns:
        List of dicts with: corp_code, name, name_kr.
    """
    return [
        {
            "corp_code": code,
            "name": info["name"],
            "name_kr": info["name_kr"],
        }
        for code, info in sorted(CORP_CODE_MAP.items(), key=lambda x: x[1]["name"])
    ]


def clear_dart_cache() -> int:
    """Clear the DART filing cache. Returns the number of evicted entries."""
    count = len(_cache)
    _cache.clear()
    logger.info("DART cache cleared (%d entries evicted)", count)
    return count
