# @TASK RSS-T2 - RSS Feed API endpoint
# @SPEC docs/planning/02-trd.md#rss-feeds
# @TEST tests/test_rss.py

"""RSS Feed API router.

Exposes a single endpoint that returns the latest semiconductor industry
news aggregated from multiple RSS sources.
"""

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.models.user import User
from app.services.rss_service import fetch_rss_feeds

router = APIRouter()


@router.get("/rss-feeds")
async def list_rss_feeds(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of RSS feed items to return",
    ),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return the latest semiconductor industry RSS feed items.

    Aggregates entries from SemiWiki, EE Times, AnandTech,
    SemiEngineering, and Tom's Hardware. Results are sorted by
    publication date (newest first).

    Requires authentication via JWT Bearer token.
    """
    items = await fetch_rss_feeds(limit=limit)
    return items
