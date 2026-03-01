# @TASK EDGAR-1 - SEC EDGAR integration for US semiconductor company filings
# @SPEC SEC EDGAR EFTS API: https://efts.sec.gov/LATEST/ and submissions API

"""SEC EDGAR integration service.

Fetches public company filings (10-K, 10-Q, 8-K) from the SEC EDGAR system
for US semiconductor companies tracked by Memory SCM.

SEC EDGAR is free and requires no API key, but mandates a User-Agent header
with a company name and contact email on every request.

Rate limit: SEC allows a maximum of 10 requests per second.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

# SEC EDGAR submissions API base URL
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# SEC EDGAR filing viewer base URL
EDGAR_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primary_doc}"
EDGAR_FILING_PAGE_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={filing_type}&dateb=&owner=include&count={count}"

# SEC requires a User-Agent header identifying the requester
SEC_USER_AGENT = "MemorySCM admin@memory-scm.com"

# Ticker -> CIK mapping for tracked US semiconductor companies
# CIK numbers are zero-padded to 10 digits for the API
TICKER_CIK_MAP: dict[str, dict] = {
    "MU": {
        "cik": "0000723125",
        "name": "Micron Technology Inc",
    },
    "INTC": {
        "cik": "0000050863",
        "name": "Intel Corp",
    },
    "AMAT": {
        "cik": "0000006951",
        "name": "Applied Materials Inc",
    },
    "LRCX": {
        "cik": "0000707549",
        "name": "Lam Research Corp",
    },
    "TSM": {
        "cik": "0001046179",
        "name": "Taiwan Semiconductor Manufacturing Co (ADR)",
    },
    "ASML": {
        "cik": "0000937966",
        "name": "ASML Holding NV (ADR)",
    },
    "AMKR": {
        "cik": "0001047127",
        "name": "Amkor Technology Inc",
    },
}

# Default filing types to fetch
DEFAULT_FILING_TYPES: list[str] = ["10-K", "10-Q", "8-K"]

# Module-level cache: key -> (timestamp, data)
_cache: dict[str, tuple[datetime, list[dict]]] = {}
CACHE_TTL = timedelta(hours=6)

# Rate-limiting: track last request time to stay under 10 req/s
_last_request_time: float = 0.0
_REQUEST_INTERVAL: float = 0.12  # ~8 requests/sec, safely under 10


def _build_cache_key(ticker: str | None, filing_types: list[str], limit: int) -> str:
    """Build a deterministic cache key."""
    ticker_part = ticker.upper() if ticker else "ALL"
    types_part = ",".join(sorted(t.upper() for t in filing_types))
    return f"edgar:{ticker_part}:{types_part}:{limit}"


def _get_cached(key: str) -> list[dict] | None:
    """Return cached data if present and not expired, otherwise None."""
    if key in _cache:
        cached_time, cached_data = _cache[key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            logger.debug("Cache hit for EDGAR key: %s", key)
            return cached_data
        del _cache[key]
    return None


def _set_cached(key: str, data: list[dict]) -> None:
    """Store data in the module-level cache."""
    _cache[key] = (datetime.now(timezone.utc), data)


async def _rate_limit_wait() -> None:
    """Wait if necessary to comply with SEC's 10 requests/second limit."""
    global _last_request_time
    import time

    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _REQUEST_INTERVAL:
        await asyncio.sleep(_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _parse_filing(
    filing_type: str,
    filing_date: str,
    accession_number: str,
    primary_document: str,
    description: str,
    cik: str,
    company_name: str,
    ticker: str,
) -> dict:
    """Parse a single filing into a structured dict.

    Args:
        filing_type: e.g. "10-K", "10-Q", "8-K".
        filing_date: Date string in "YYYY-MM-DD" format.
        accession_number: SEC accession number (with dashes).
        primary_document: Primary document filename.
        description: Filing description/title.
        cik: Company CIK number.
        company_name: Human-readable company name.
        ticker: Stock ticker symbol.

    Returns:
        Structured dict with filing metadata and URL.
    """
    # Build direct link to the filing document
    accession_no_dashes = accession_number.replace("-", "")
    doc_url = EDGAR_ARCHIVES_URL.format(
        cik=cik.lstrip("0"),
        accession_no_dashes=accession_no_dashes,
        primary_doc=primary_document,
    )

    return {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "filing_type": filing_type,
        "title": description if description else f"{company_name} {filing_type}",
        "date": filing_date,
        "accession_number": accession_number,
        "url": doc_url,
    }


async def get_company_filings(
    ticker: str,
    filing_types: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    """Fetch recent SEC filings for a specific company by ticker.

    Uses the SEC EDGAR submissions API to retrieve filing metadata.

    Args:
        ticker: Stock ticker symbol (e.g. "MU", "INTC").
        filing_types: List of filing types to include (e.g. ["10-K", "10-Q"]).
            Defaults to 10-K, 10-Q, and 8-K.
        limit: Maximum number of filings to return.

    Returns:
        List of filing dicts with: ticker, company_name, filing_type, title,
        date, accession_number, url.

    Raises:
        ValueError: If the ticker is not in the supported company map.
    """
    ticker = ticker.upper()
    if filing_types is None:
        filing_types = DEFAULT_FILING_TYPES

    filing_types_upper = [ft.upper() for ft in filing_types]

    if ticker not in TICKER_CIK_MAP:
        supported = ", ".join(sorted(TICKER_CIK_MAP.keys()))
        raise ValueError(
            f"Ticker '{ticker}' is not supported. "
            f"Supported tickers: {supported}"
        )

    company_info = TICKER_CIK_MAP[ticker]
    cik = company_info["cik"]
    company_name = company_info["name"]

    # Check cache first
    cache_key = _build_cache_key(ticker, filing_types_upper, limit)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = EDGAR_SUBMISSIONS_URL.format(cik=cik)

    try:
        await _rate_limit_wait()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": SEC_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

    except httpx.TimeoutException:
        logger.warning(
            "SEC EDGAR API request timed out for ticker=%s (CIK=%s)",
            ticker,
            cik,
        )
        return []
    except httpx.HTTPStatusError as exc:
        logger.error(
            "SEC EDGAR API returned HTTP %d for ticker=%s: %s",
            exc.response.status_code,
            ticker,
            exc.response.text[:200],
        )
        return []
    except httpx.HTTPError as exc:
        logger.error("Network error calling SEC EDGAR API for ticker=%s: %s", ticker, exc)
        return []
    except (ValueError, KeyError) as exc:
        logger.error("Failed to parse SEC EDGAR response for ticker=%s: %s", ticker, exc)
        return []

    # Parse the recent filings from the submissions response
    recent = data.get("filings", {}).get("recent", {})
    if not recent:
        logger.info("No recent filings found for ticker=%s (CIK=%s)", ticker, cik)
        return []

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    filings: list[dict] = []
    for i in range(len(forms)):
        form_type = forms[i] if i < len(forms) else ""
        if form_type.upper() not in filing_types_upper:
            continue

        filing_date = dates[i] if i < len(dates) else ""
        accession = accession_numbers[i] if i < len(accession_numbers) else ""
        primary_doc = primary_documents[i] if i < len(primary_documents) else ""
        description = descriptions[i] if i < len(descriptions) else ""

        filings.append(
            _parse_filing(
                filing_type=form_type,
                filing_date=filing_date,
                accession_number=accession,
                primary_document=primary_doc,
                description=description,
                cik=cik,
                company_name=company_name,
                ticker=ticker,
            )
        )

        if len(filings) >= limit:
            break

    logger.info(
        "Fetched %d filings for %s (%s) from SEC EDGAR",
        len(filings),
        ticker,
        company_name,
    )

    _set_cached(cache_key, filings)
    return filings


async def get_all_semiconductor_filings(
    limit_per_company: int = 5,
    filing_types: list[str] | None = None,
) -> list[dict]:
    """Fetch recent filings for all tracked semiconductor companies.

    Iterates through the TICKER_CIK_MAP and fetches filings for each company.
    Results are cached for 6 hours at the aggregate level.

    Args:
        limit_per_company: Maximum filings per company.
        filing_types: List of filing types to include. Defaults to 10-K, 10-Q, 8-K.

    Returns:
        Combined list of filing dicts from all companies, sorted by date descending.
    """
    if filing_types is None:
        filing_types = DEFAULT_FILING_TYPES

    # Check aggregate cache
    cache_key = _build_cache_key(None, filing_types, limit_per_company)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    all_filings: list[dict] = []

    for ticker in TICKER_CIK_MAP:
        try:
            company_filings = await get_company_filings(
                ticker=ticker,
                filing_types=filing_types,
                limit=limit_per_company,
            )
            all_filings.extend(company_filings)
        except Exception:
            logger.exception(
                "Failed to fetch filings for %s, skipping", ticker
            )
            continue

    # Sort all filings by date descending
    all_filings.sort(key=lambda f: f.get("date", ""), reverse=True)

    logger.info(
        "Fetched %d total filings across %d semiconductor companies",
        len(all_filings),
        len(TICKER_CIK_MAP),
    )

    _set_cached(cache_key, all_filings)
    return all_filings


def get_supported_tickers() -> list[dict]:
    """Return the list of supported tickers and company names.

    Returns:
        List of dicts with: ticker, name, cik.
    """
    return [
        {"ticker": ticker, "name": info["name"], "cik": info["cik"]}
        for ticker, info in sorted(TICKER_CIK_MAP.items())
    ]


def clear_edgar_cache() -> int:
    """Clear the EDGAR filing cache. Returns the number of evicted entries."""
    count = len(_cache)
    _cache.clear()
    logger.info("EDGAR cache cleared (%d entries evicted)", count)
    return count
