# @TASK GDELT-2 - GDELT geopolitical events API endpoint
# @TEST tests/test_gdelt.py

"""GDELT geopolitical events API router.

Exposes endpoints that return geopolitical events from the GDELT Project
that may impact the semiconductor supply chain.
"""

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.models.user import User
from app.services.gdelt_service import (
    DEFAULT_KEYWORDS,
    fetch_geopolitical_events,
    get_semiconductor_risk_events,
)

router = APIRouter()


@router.get("/geopolitical-events")
async def get_geopolitical_events(
    keywords: str | None = Query(
        default=None,
        description=(
            "Comma-separated list of keywords to search. "
            "Defaults to: semiconductor export control, chip ban, "
            "Taiwan strait, TSMC risk, chip shortage"
        ),
    ),
    timespan: str = Query(
        default="24h",
        description=(
            "Time window for results. Examples: '24h', '48h', '7d'. "
            "Defaults to 24 hours."
        ),
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of events to return (1-100).",
    ),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return geopolitical events affecting the semiconductor supply chain.

    Fetches real-time event data from the GDELT Global Knowledge Graph API.
    Events include export controls, trade disputes, geopolitical tensions,
    and other factors that may impact semiconductor supply chains.

    Requires authentication via JWT Bearer token.
    """
    if keywords:
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        events = await fetch_geopolitical_events(
            keywords=keyword_list,
            timespan=timespan,
            limit=limit,
        )
    else:
        # Use default semiconductor keywords with caching
        events = await get_semiconductor_risk_events(
            limit=limit,
            timespan=timespan,
        )

    return {
        "count": len(events),
        "timespan": timespan,
        "keywords": keyword_list if keywords else DEFAULT_KEYWORDS,
        "events": events,
    }
