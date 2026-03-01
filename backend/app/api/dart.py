# @TASK DART-2 - DART Korean semiconductor filings API endpoints
# @TEST tests/test_dart.py

"""DART (Korea FSS) filings API router.

Exposes endpoints for querying Korean public company filings from the
Financial Supervisory Service's DART electronic disclosure system.
Covers Korean semiconductor companies tracked by Memory SCM.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user
from app.models.user import User
from app.services.dart_service import (
    CORP_CODE_MAP,
    get_all_kr_semiconductor_filings,
    get_company_filings,
    get_supported_companies,
)

router = APIRouter()


@router.get("/dart-filings")
async def list_all_dart_filings(
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of filings per company (1-20).",
    ),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return recent DART filings for all tracked Korean semiconductor companies.

    Aggregates filings from Samsung Electronics, SK hynix, Samsung SDI,
    LG Innotek, and other Korean semiconductor companies. Results are
    cached for 6 hours to minimize load on the DART API.

    Requires authentication via JWT Bearer token.
    """
    filings = await get_all_kr_semiconductor_filings(
        limit_per_company=limit,
    )

    companies = get_supported_companies()

    return {
        "count": len(filings),
        "limit_per_company": limit,
        "companies": [c["name"] for c in companies],
        "filings": filings,
    }


@router.get("/dart-filings/companies")
async def list_supported_kr_companies(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the list of supported Korean semiconductor companies and their DART corp codes.

    Requires authentication via JWT Bearer token.
    """
    companies = get_supported_companies()
    return {
        "count": len(companies),
        "companies": companies,
    }


@router.get("/dart-filings/{corp_code}")
async def get_filings_by_corp_code(
    corp_code: str,
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of filings to return (1-50).",
    ),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return recent DART filings for a specific Korean semiconductor company.

    Fetches filings from DART for the given corporation code. Only corp codes
    in the supported company map are accepted.

    Requires authentication via JWT Bearer token.
    """
    if corp_code not in CORP_CODE_MAP:
        supported_list = get_supported_companies()
        supported_display = ", ".join(
            f"{c['name']} ({c['corp_code']})" for c in supported_list[:5]
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"Corporation code '{corp_code}' is not supported. "
                f"Examples of supported codes: {supported_display}..."
            ),
        )

    try:
        filings = await get_company_filings(
            corp_code=corp_code,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    company_info = CORP_CODE_MAP[corp_code]

    return {
        "corp_code": corp_code,
        "corp_name": company_info["name"],
        "corp_name_kr": company_info["name_kr"],
        "count": len(filings),
        "filings": filings,
    }
