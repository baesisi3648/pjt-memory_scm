"""NewsAPI.org integration service.

Fetches real news articles for semiconductor companies and caches them in the DB.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"
CACHE_TTL_HOURS = 6


async def fetch_company_news(
    session: Session,
    company_id: int,
    company_name: str,
    limit: int = 10,
) -> list[NewsItem]:
    """Fetch news for a company. Uses DB cache if fresh, otherwise calls NewsAPI."""

    # Check for cached news less than CACHE_TTL_HOURS old
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)
    cached = session.exec(
        select(NewsItem)
        .where(NewsItem.company_id == company_id)
        .where(NewsItem.created_at >= cutoff)
        .order_by(NewsItem.published_at.desc())
        .limit(limit)
    ).all()

    if cached:
        return list(cached)

    # No fresh cache — fetch from API
    if not company_name:
        return []

    # Try NewsAPI first (if key configured), then Google News RSS as fallback
    if settings.NEWS_API_KEY:
        articles = await _call_newsapi(company_name, limit)
    else:
        articles = await _call_google_news_rss(company_name, limit)

    if not articles:
        # Return stale cache if API returns nothing
        return list(
            session.exec(
                select(NewsItem)
                .where(NewsItem.company_id == company_id)
                .order_by(NewsItem.published_at.desc())
                .limit(limit)
            ).all()
        )

    # Delete old cached news for this company, then insert fresh results
    old_items = session.exec(
        select(NewsItem).where(NewsItem.company_id == company_id)
    ).all()
    for item in old_items:
        session.delete(item)

    now = datetime.now(timezone.utc)
    new_items: list[NewsItem] = []
    for article in articles[:limit]:
        published = None
        if article.get("publishedAt"):
            try:
                published = datetime.fromisoformat(
                    article["publishedAt"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        news_item = NewsItem(
            title=article.get("title", "")[:500],
            url=article.get("url", ""),
            source=article.get("source", {}).get("name", "")[:255] if article.get("source") else None,
            company_id=company_id,
            published_at=published,
            created_at=now,
        )
        session.add(news_item)
        new_items.append(news_item)

    session.commit()
    for item in new_items:
        session.refresh(item)

    return new_items


async def _call_google_news_rss(company_name: str, limit: int = 10) -> list[dict]:
    """Fetch news via Google News RSS (free, no API key required)."""
    from urllib.parse import quote
    import feedparser

    # Use exact match for company name + broad industry terms
    query = f'"{company_name}" (semiconductor OR chip OR 반도체)'
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en&gl=US&ceid=US:en"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:limit]:
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                from time import mktime
                published_at = datetime.fromtimestamp(
                    mktime(entry.published_parsed), tz=timezone.utc
                ).isoformat()

            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "source": {"name": entry.get("source", {}).get("title", "Google News")
                           if hasattr(entry, "source") else "Google News"},
                "publishedAt": published_at,
            })
        return articles

    except Exception:
        logger.exception("Error fetching Google News RSS for %r", company_name)
        return []


INDUSTRY_KEYWORDS = "semiconductor OR chip OR memory OR DRAM OR NAND OR HBM OR wafer OR foundry OR 반도체"


async def _call_newsapi(company_name: str, page_size: int = 10) -> list[dict]:
    """Call NewsAPI.org /v2/everything with industry-scoped query."""
    # Combine company name with industry keywords for relevant results
    query = f'"{company_name}" AND ({INDUSTRY_KEYWORDS})'

    params = {
        "q": query,
        "pageSize": min(page_size, 20),
        "sortBy": "publishedAt",
        "apiKey": settings.NEWS_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(NEWSAPI_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])

            # Filter out removed/empty articles
            return [
                a for a in articles
                if a.get("title") and a["title"] != "[Removed]"
                and a.get("url")
            ]
    except httpx.HTTPStatusError as exc:
        logger.error(
            "NewsAPI returned HTTP %d for company=%r: %s",
            exc.response.status_code,
            company_name,
            exc.response.text[:200],
        )
        return []
    except httpx.HTTPError as exc:
        logger.error(
            "Network error calling NewsAPI for company=%r: %s",
            company_name,
            exc,
        )
        return []
    except Exception:
        logger.exception("Unexpected error calling NewsAPI for company=%r", company_name)
        return []
