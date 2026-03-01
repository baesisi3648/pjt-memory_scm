# @TASK EXCHANGE-T1 - Frankfurter exchange rate service
# @SPEC https://www.frankfurter.app/docs/ - free, no API key required

"""Exchange rate service using frankfurter.app with in-memory caching."""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 30 * 60  # 30 minutes

BASE_CURRENCY = "USD"
TARGET_CURRENCIES = "KRW,JPY,TWD,EUR"
FRANKFURTER_URL = (
    f"https://api.frankfurter.app/latest?from={BASE_CURRENCY}&to={TARGET_CURRENCIES}"
)

# Simple in-memory cache: (timestamp, rates_dict)
# rates_dict maps currency code -> float exchange rate
_cache: tuple[float, dict[str, float]] | None = None


def _is_cache_valid() -> bool:
    """Check whether the cached exchange rate data is still within TTL."""
    if _cache is None:
        return False
    cached_time, _ = _cache
    return (time.time() - cached_time) < CACHE_TTL_SECONDS


def fetch_exchange_rates() -> dict[str, float] | None:
    """
    Fetch the latest USD-based exchange rates from frankfurter.app.

    Returns a dict mapping currency codes to float rates on success,
    or None if the API call fails or returns unexpected data.
    Results are cached in memory for 30 minutes.

    Layer 2: Domain validation - API response must contain 'rates' key
    Layer 4: Structured logging for traceability
    """
    global _cache

    # Return cached data when it is still valid
    if _is_cache_valid():
        _, cached_rates = _cache  # type: ignore[misc]
        logger.debug("Cache hit for exchange rates")
        return cached_rates

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(FRANKFURTER_URL)
            response.raise_for_status()

        payload = response.json()
        rates: dict[str, float] | None = payload.get("rates")

        if not rates or not isinstance(rates, dict):
            logger.warning(
                "Unexpected response structure from frankfurter.app: %s", payload
            )
            return None

        # Normalise all values to plain Python floats
        normalised: dict[str, float] = {k: float(v) for k, v in rates.items()}

        # Store in cache
        _cache = (time.time(), normalised)
        logger.info(
            "Fetched exchange rates from frankfurter.app: %s",
            ", ".join(f"{k}={v}" for k, v in normalised.items()),
        )
        return normalised

    except Exception:
        logger.exception("Failed to fetch exchange rates from frankfurter.app")
        return None


def clear_cache() -> None:
    """Clear the exchange rate cache. Useful for testing."""
    global _cache
    _cache = None
