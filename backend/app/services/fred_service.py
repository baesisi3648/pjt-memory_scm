# @TASK FRED-1 - FRED API service for semiconductor-related macro indicators
# @SPEC https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""FRED API service for semiconductor-related macro indicators."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Key semiconductor macro indicators
FRED_SERIES = {
    "ISM_PMI": {"id": "MANEMP", "name": "Manufacturing Employment", "unit": "thousands"},
    "SEMI_SHIP": {"id": "AMTMNO", "name": "New Orders: Manufacturing", "unit": "millions USD"},
    "INDPRO": {"id": "INDPRO", "name": "Industrial Production Index", "unit": "index"},
    "PCU3344": {"id": "PCU33443344", "name": "PPI: Semiconductor Manufacturing", "unit": "index"},
    "USD_KRW": {"id": "DEXKOUS", "name": "KRW/USD Exchange Rate", "unit": "KRW"},
    "USD_JPY": {"id": "DEXJPUS", "name": "JPY/USD Exchange Rate", "unit": "JPY"},
}

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Simple in-memory cache (1 hour TTL)
_cache: dict[str, tuple[datetime, list]] = {}
CACHE_TTL = timedelta(hours=1)


async def fetch_fred_series(
    series_id: str,
    limit: int = 30,
) -> list[dict]:
    """Fetch observations for a FRED series."""
    if not settings.FRED_API_KEY:
        logger.warning("FRED_API_KEY not set, returning empty data")
        return []

    # Check cache
    cache_key = f"{series_id}:{limit}"
    if cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            return cached_data

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                BASE_URL,
                params={
                    "series_id": series_id,
                    "api_key": settings.FRED_API_KEY,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": limit,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        observations = [
            {
                "date": obs["date"],
                "value": float(obs["value"]) if obs["value"] != "." else None,
            }
            for obs in data.get("observations", [])
            if obs.get("value") != "."
        ]

        _cache[cache_key] = (datetime.now(timezone.utc), observations)
        return observations

    except httpx.HTTPError as e:
        logger.error("FRED API error for %s: %s", series_id, str(e))
        return []
    except Exception as e:
        logger.error("Unexpected error fetching FRED %s: %s", series_id, str(e))
        return []


async def fetch_all_indicators() -> dict:
    """Fetch all configured FRED indicators."""
    result = {}
    for key, meta in FRED_SERIES.items():
        observations = await fetch_fred_series(meta["id"], limit=30)
        result[key] = {
            "name": meta["name"],
            "unit": meta["unit"],
            "series_id": meta["id"],
            "observations": observations,
        }
    return result
