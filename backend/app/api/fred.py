# @TASK FRED-2 - FRED macro indicator API endpoints
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user
from app.models.user import User
from app.services.fred_service import (
    FRED_SERIES,
    fetch_all_indicators,
    fetch_fred_series,
)

router = APIRouter()


@router.get("/macro-indicators")
async def get_macro_indicators(
    current_user: User = Depends(get_current_user),
):
    """Get all FRED macro indicators for semiconductor industry."""
    return await fetch_all_indicators()


@router.get("/macro-indicators/{series_key}")
async def get_indicator(
    series_key: str,
    limit: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
):
    """Get a specific FRED indicator by key."""
    if series_key not in FRED_SERIES:
        raise HTTPException(status_code=404, detail=f"Unknown indicator: {series_key}")

    meta = FRED_SERIES[series_key]
    observations = await fetch_fred_series(meta["id"], limit=limit)
    return {
        "name": meta["name"],
        "unit": meta["unit"],
        "series_id": meta["id"],
        "observations": observations,
    }
