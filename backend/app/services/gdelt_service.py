# @TASK GDELT-1 - GDELT Project integration for geopolitical event monitoring
# @SPEC GDELT GKG (Global Knowledge Graph) API for semiconductor supply chain risk events

"""GDELT Project integration service.

Fetches geopolitical events from the GDELT Global Knowledge Graph API that
may impact the semiconductor supply chain (export controls, trade disputes,
geopolitical tensions near key manufacturing hubs).

GDELT API is free and requires no API key.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

DEFAULT_KEYWORDS: list[str] = [
    "semiconductor export control",
    "chip ban",
    "Taiwan strait",
    "TSMC risk",
    "chip shortage",
]

# Simple module-level cache: key -> (timestamp, data)
_cache: dict[str, tuple[datetime, list[dict]]] = {}
CACHE_TTL = timedelta(hours=1)


def _build_cache_key(keywords: list[str], timespan: str) -> str:
    """Build a deterministic cache key from keywords and timespan."""
    sorted_kw = ",".join(sorted(k.lower() for k in keywords))
    return f"gdelt:{sorted_kw}:{timespan}"


def _get_cached(key: str) -> list[dict] | None:
    """Return cached data if present and not expired, otherwise None."""
    if key in _cache:
        cached_time, cached_data = _cache[key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            logger.debug("Cache hit for GDELT key: %s", key)
            return cached_data
        # Expired - remove stale entry
        del _cache[key]
    return None


def _set_cached(key: str, data: list[dict]) -> None:
    """Store data in the module-level cache."""
    _cache[key] = (datetime.now(timezone.utc), data)


def _parse_gdelt_article(article: dict) -> dict:
    """Parse a single GDELT article into a structured event dict.

    Args:
        article: Raw article dict from GDELT API response.

    Returns:
        Structured dict with: title, url, source, date, tone, themes, language,
        image_url, domain.
    """
    # Tone: GDELT provides a tone score (positive = positive sentiment)
    tone_value = None
    raw_tone = article.get("tone")
    if raw_tone is not None:
        try:
            tone_value = round(float(raw_tone), 2)
        except (ValueError, TypeError):
            pass

    # Socialimage may be present
    image_url = article.get("socialimage", "")

    return {
        "title": article.get("title", ""),
        "url": article.get("url", ""),
        "source": article.get("sourcecountry", article.get("domain", "")),
        "domain": article.get("domain", ""),
        "date": article.get("seendate", ""),
        "tone": tone_value,
        "themes": [],
        "language": article.get("language", ""),
        "image_url": image_url if image_url else None,
    }


async def fetch_geopolitical_events(
    keywords: list[str] | None = None,
    timespan: str = "24h",
    limit: int = 20,
) -> list[dict]:
    """Fetch geopolitical events from the GDELT GKG API.

    Args:
        keywords: Search keywords. Defaults to semiconductor-related terms.
        timespan: Time window for results (e.g. "24h", "48h", "7d").
        limit: Maximum number of events to return.

    Returns:
        A list of structured event dicts with: title, url, source, date,
        tone (sentiment score), themes, language, image_url, domain.
    """
    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    # Build GDELT query: OR-join all keywords
    query = " OR ".join(f'"{kw}"' for kw in keywords)

    # Convert timespan to GDELT-compatible format (minutes)
    timespan_minutes = _parse_timespan_to_minutes(timespan)

    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "timespan": f"{timespan_minutes}min",
        "maxrecords": str(min(limit, 250)),
        "sort": "DateDesc",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(GDELT_DOC_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        articles = data.get("articles", [])
        if not articles:
            logger.info("GDELT returned no articles for query: %s", query)
            return []

        events = [_parse_gdelt_article(a) for a in articles[:limit]]

        # Filter out entries with no title
        events = [e for e in events if e["title"]]

        logger.info(
            "Fetched %d geopolitical events from GDELT for %d keywords",
            len(events),
            len(keywords),
        )
        return events

    except httpx.TimeoutException:
        logger.warning(
            "GDELT API request timed out (keywords=%s, timespan=%s)",
            keywords,
            timespan,
        )
        return []
    except httpx.HTTPStatusError as exc:
        logger.error(
            "GDELT API returned HTTP %d: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return []
    except httpx.HTTPError as exc:
        logger.error("Network error calling GDELT API: %s", exc)
        return []
    except (ValueError, KeyError) as exc:
        # JSON parsing errors (GDELT sometimes returns non-JSON on errors)
        logger.error("Failed to parse GDELT response: %s", exc)
        return []
    except Exception:
        logger.exception("Unexpected error calling GDELT API")
        return []


async def get_semiconductor_risk_events(
    limit: int = 20,
    timespan: str = "24h",
) -> list[dict]:
    """Fetch semiconductor supply-chain risk events with caching.

    Uses the default semiconductor-related keywords and caches results
    for 1 hour to reduce API calls to GDELT.

    Args:
        limit: Maximum number of events to return.
        timespan: Time window for results.

    Returns:
        Cached or freshly-fetched list of geopolitical event dicts.
    """
    cache_key = _build_cache_key(DEFAULT_KEYWORDS, timespan)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached[:limit]

    # Fetch a larger batch for caching, then slice to requested limit
    events = await fetch_geopolitical_events(
        keywords=DEFAULT_KEYWORDS,
        timespan=timespan,
        limit=250,
    )

    # Cache even empty results to avoid hammering GDELT on repeated failures
    _set_cached(cache_key, events)
    return events[:limit]


def _parse_timespan_to_minutes(timespan: str) -> int:
    """Convert a human-friendly timespan string to minutes.

    Supports formats like "24h", "48h", "7d", "30m".
    Defaults to 1440 (24 hours) on parse failure.
    """
    timespan = timespan.strip().lower()
    try:
        if timespan.endswith("h"):
            return int(timespan[:-1]) * 60
        elif timespan.endswith("d"):
            return int(timespan[:-1]) * 1440
        elif timespan.endswith("m"):
            return int(timespan[:-1])
        else:
            # Try interpreting as hours for backward compatibility
            return int(timespan) * 60
    except (ValueError, TypeError):
        logger.warning("Invalid timespan %r, defaulting to 24h", timespan)
        return 1440


def clear_gdelt_cache() -> int:
    """Clear the GDELT event cache. Returns the number of evicted entries."""
    count = len(_cache)
    _cache.clear()
    logger.info("GDELT cache cleared (%d entries evicted)", count)
    return count
