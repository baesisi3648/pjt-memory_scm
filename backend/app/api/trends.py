# @TASK TRENDS-2 - Google Trends API endpoint
# @TEST tests/test_trends.py

"""Google Trends API router.

Exposes an endpoint that returns Google Trends interest-over-time data
for semiconductor-related keywords.
"""

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.models.user import User
from app.services.trends_service import DEFAULT_KEYWORDS, get_keyword_trends

router = APIRouter()


@router.get("/trends")
async def get_trends(
    keywords: str | None = Query(
        default=None,
        description=(
            "Comma-separated list of keywords (max 5). "
            "Defaults to: DRAM, HBM, semiconductor, AI chip"
        ),
    ),
    timeframe: str = Query(
        default="today 3-m",
        description=(
            "Timeframe for trend data. Examples: "
            "'today 3-m', 'today 12-m', '2024-01-01 2025-01-01'"
        ),
    ),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return Google Trends interest-over-time data for semiconductor keywords.

    The response is a list of objects with date, keyword, and value fields.
    Values are relative interest scores from 0 to 100.

    Requires authentication via JWT Bearer token.
    """
    if keywords:
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    else:
        keyword_list = DEFAULT_KEYWORDS

    data = await get_keyword_trends(keywords=keyword_list, timeframe=timeframe)
    return data
