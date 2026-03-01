# @TASK RSS-T1 - RSS Feed collector service for semiconductor industry news
# @SPEC docs/planning/02-trd.md#rss-feeds

"""RSS Feed collector service.

Aggregates semiconductor industry news from multiple RSS sources,
normalizes entries into a common format, and returns them sorted
by publication date (newest first).
"""

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"name": "SemiWiki", "url": "https://semiwiki.com/feed/"},
    {"name": "EE Times", "url": "https://www.eetimes.com/feed/"},
    {"name": "AnandTech", "url": "https://www.anandtech.com/rss/"},
    {"name": "SemiEngineering", "url": "https://semiengineering.com/feed/"},
    {"name": "Tom's Hardware", "url": "https://www.tomshardware.com/feeds/all"},
]


def _parse_published_date(entry: feedparser.FeedParserDict) -> str:
    """Extract and normalize the published date from a feed entry.

    Checks ``published_parsed`` and ``updated_parsed`` struct-time fields.
    Falls back to the current UTC time when neither is available.

    Returns:
        ISO-8601 formatted datetime string.
    """
    time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if time_struct:
        try:
            dt = datetime.fromtimestamp(mktime(time_struct), tz=timezone.utc)
            return dt.isoformat()
        except (ValueError, OverflowError, OSError) as exc:
            logger.warning(
                "Failed to parse date from entry %r: %s",
                entry.get("title", "<no title>"),
                exc,
            )
    # Fallback: current UTC time
    return datetime.now(timezone.utc).isoformat()


def _clean_summary(entry: feedparser.FeedParserDict) -> str:
    """Return a plain-text summary, truncated to 500 characters."""
    raw = entry.get("summary") or entry.get("description") or ""
    # feedparser may return HTML; strip it to keep the response lightweight.
    # A simple approach: use the value attribute if available.
    text = raw[:500]
    return text


async def fetch_rss_feeds(limit: int = 20) -> list[dict]:
    """Fetch and aggregate RSS feed entries from all configured sources.

    Args:
        limit: Maximum number of entries to return (already sorted by date).

    Returns:
        A list of dicts, each containing:
        - title (str)
        - url (str)
        - source (str): human-readable feed name
        - published_at (str): ISO-8601 datetime
        - summary (str): first 500 chars of the entry summary
    """
    all_entries: list[dict] = []

    for feed_config in RSS_FEEDS:
        feed_name = feed_config["name"]
        feed_url = feed_config["url"]

        try:
            parsed = feedparser.parse(feed_url)

            if parsed.bozo and not parsed.entries:
                logger.warning(
                    "RSS feed %r (%s) returned a bozo error: %s",
                    feed_name,
                    feed_url,
                    parsed.bozo_exception,
                )
                continue

            for entry in parsed.entries:
                title = entry.get("title")
                link = entry.get("link")
                if not title or not link:
                    continue

                all_entries.append(
                    {
                        "title": title,
                        "url": link,
                        "source": feed_name,
                        "published_at": _parse_published_date(entry),
                        "summary": _clean_summary(entry),
                    }
                )

            logger.info(
                "Fetched %d entries from RSS feed %r",
                len(parsed.entries),
                feed_name,
            )

        except Exception:
            logger.exception(
                "Unexpected error fetching RSS feed %r (%s)",
                feed_name,
                feed_url,
            )

    # Sort by published_at descending (newest first)
    all_entries.sort(key=lambda e: e["published_at"], reverse=True)

    return all_entries[:limit]
