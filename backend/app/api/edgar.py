# @TASK EDGAR-2 - SEC EDGAR filings API endpoints
# @TEST tests/test_edgar.py

"""SEC EDGAR filings API router.

Exposes endpoints for querying SEC filings (10-K, 10-Q, 8-K) of US
semiconductor companies tracked by Memory SCM.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user
from app.models.user import User
from app.services.edgar_service import (
    DEFAULT_FILING_TYPES,
    TICKER_CIK_MAP,
    get_all_semiconductor_filings,
    get_company_filings,
    get_supported_tickers,
)

router = APIRouter()


@router.get("/sec-filings")
async def list_all_filings(
    filing_types: str | None = Query(
        default=None,
        description=(
            "Comma-separated list of filing types to include. "
            "Defaults to: 10-K, 10-Q, 8-K. "
            "Example: '10-K,10-Q'"
        ),
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of filings per company (1-20).",
    ),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return recent SEC filings for all tracked semiconductor companies.

    Aggregates filings from Micron, Intel, Applied Materials, Lam Research,
    TSMC (ADR), ASML (ADR), and Amkor Technology. Results are cached for
    6 hours to minimize load on SEC EDGAR.

    Requires authentication via JWT Bearer token.
    """
    types_list = _parse_filing_types(filing_types)

    filings = await get_all_semiconductor_filings(
        limit_per_company=limit,
        filing_types=types_list,
    )

    return {
        "count": len(filings),
        "limit_per_company": limit,
        "filing_types": types_list,
        "companies": [t["ticker"] for t in get_supported_tickers()],
        "filings": filings,
    }


@router.get("/sec-filings/companies")
async def list_supported_companies(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the list of supported semiconductor companies and their CIK numbers.

    Requires authentication via JWT Bearer token.
    """
    tickers = get_supported_tickers()
    return {
        "count": len(tickers),
        "companies": tickers,
    }


@router.get("/sec-filings/{ticker}")
async def get_filings_by_ticker(
    ticker: str,
    filing_types: str | None = Query(
        default=None,
        description=(
            "Comma-separated list of filing types to include. "
            "Defaults to: 10-K, 10-Q, 8-K."
        ),
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of filings to return (1-50).",
    ),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return recent SEC filings for a specific semiconductor company.

    Fetches filings from SEC EDGAR for the given ticker symbol. Only
    tickers in the supported company map are accepted.

    Requires authentication via JWT Bearer token.
    """
    ticker_upper = ticker.upper()

    if ticker_upper not in TICKER_CIK_MAP:
        supported = ", ".join(sorted(TICKER_CIK_MAP.keys()))
        raise HTTPException(
            status_code=404,
            detail=(
                f"Ticker '{ticker_upper}' is not supported. "
                f"Supported tickers: {supported}"
            ),
        )

    types_list = _parse_filing_types(filing_types)

    try:
        filings = await get_company_filings(
            ticker=ticker_upper,
            filing_types=types_list,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    company_info = TICKER_CIK_MAP[ticker_upper]

    return {
        "ticker": ticker_upper,
        "company_name": company_info["name"],
        "count": len(filings),
        "filing_types": types_list,
        "filings": filings,
    }


def _parse_filing_types(raw: str | None) -> list[str]:
    """Parse a comma-separated filing_types query param into a list.

    Returns the default filing types if the input is None or empty.
    """
    if not raw:
        return DEFAULT_FILING_TYPES
    parsed = [ft.strip().upper() for ft in raw.split(",") if ft.strip()]
    return parsed if parsed else DEFAULT_FILING_TYPES
