# @TASK TRENDS-1 - Google Trends service for semiconductor search trends
# @SPEC Google Trends interest-over-time for memory/semiconductor keywords

"""Google Trends service for semiconductor keyword trends.

Fetches interest-over-time data from Google Trends using the pytrends
library and caches results for 24 hours to avoid rate limiting.
"""

import logging
from datetime import datetime, timedelta, timezone

from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

# Default semiconductor-related keywords
DEFAULT_KEYWORDS: list[str] = ["DRAM", "HBM", "semiconductor", "AI chip"]

# Simple module-level cache: key -> (timestamp, data)
_cache: dict[str, tuple[datetime, list[dict]]] = {}
CACHE_TTL = timedelta(hours=24)


def _build_cache_key(keywords: list[str], timeframe: str) -> str:
    """Build a deterministic cache key from keywords and timeframe."""
    sorted_kw = ",".join(sorted(k.lower() for k in keywords))
    return f"trends:{sorted_kw}:{timeframe}"


def _get_cached(key: str) -> list[dict] | None:
    """Return cached data if present and not expired, otherwise None."""
    if key in _cache:
        cached_time, cached_data = _cache[key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            logger.debug("Cache hit for trends key: %s", key)
            return cached_data
        # Expired - remove stale entry
        del _cache[key]
    return None


def _set_cached(key: str, data: list[dict]) -> None:
    """Store data in the module-level cache."""
    _cache[key] = (datetime.now(timezone.utc), data)


async def get_keyword_trends(
    keywords: list[str],
    timeframe: str = "today 3-m",
) -> list[dict]:
    """Fetch Google Trends interest-over-time data for the given keywords.

    Args:
        keywords: List of search terms (max 5 per Google Trends API).
        timeframe: Timeframe string for pytrends (e.g. "today 3-m",
                   "today 12-m", "2024-01-01 2024-12-31").

    Returns:
        A list of dicts, each containing:
        - date (str): ISO-8601 date string
        - keyword (str): the search term
        - value (int): relative interest score (0-100)
    """
    # Enforce Google Trends limit of 5 keywords per request
    keywords = keywords[:5]

    cache_key = _build_cache_key(keywords, timeframe)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo="", gprop="")

        df = pytrends.interest_over_time()

        if df.empty:
            logger.warning("Google Trends returned empty data for %s", keywords)
            return []

        # Drop the 'isPartial' column if present
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])

        results: list[dict] = []
        for date_idx, row in df.iterrows():
            date_str = date_idx.strftime("%Y-%m-%d")
            for kw in keywords:
                if kw in df.columns:
                    results.append(
                        {
                            "date": date_str,
                            "keyword": kw,
                            "value": int(row[kw]),
                        }
                    )

        _set_cached(cache_key, results)
        logger.info(
            "Fetched %d trend data points for keywords: %s",
            len(results),
            keywords,
        )
        return results

    except Exception as e:
        error_name = type(e).__name__
        # Handle rate limiting gracefully
        if "TooManyRequestsError" in error_name or "429" in str(e):
            logger.warning(
                "Google Trends rate limited (429). Returning empty data for %s",
                keywords,
            )
        else:
            logger.error(
                "Error fetching Google Trends data for %s: %s: %s",
                keywords,
                error_name,
                str(e),
            )
        return []


def clear_trends_cache() -> int:
    """Clear the trends cache. Returns the number of evicted entries."""
    count = len(_cache)
    _cache.clear()
    logger.info("Trends cache cleared (%d entries evicted)", count)
    return count
