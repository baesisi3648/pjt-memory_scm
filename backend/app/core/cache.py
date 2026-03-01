# @TASK PERF-1 - In-memory TTL cache for rarely-changing endpoints
# @SPEC Cachetools-based TTL cache to reduce DB load on static data

import hashlib
import json
import logging

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Shared TTL cache: entries expire after 300s (5 minutes), max 256 entries
_cache: TTLCache = TTLCache(maxsize=256, ttl=300)


def get_cached(key: str):
    """Return cached value for *key*, or ``None`` if not present / expired."""
    return _cache.get(key)


def set_cached(key: str, value):
    """Store *value* under *key* (auto-expires per TTL)."""
    _cache[key] = value


def make_cache_key(prefix: str, **params) -> str:
    """Build a deterministic cache key from *prefix* and keyword params.

    Parameters are sorted and hashed so the key stays short regardless of
    how many filter/pagination values are passed.
    """
    param_str = json.dumps(params, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(param_str.encode()).hexdigest()}"


def clear_cache() -> int:
    """Invalidate every entry in the cache.

    Returns the number of entries that were evicted.
    """
    count = len(_cache)
    _cache.clear()
    logger.info("Cache cleared (%d entries evicted)", count)
    return count
