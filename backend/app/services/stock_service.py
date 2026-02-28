# @TASK STOCK-T1 - Yahoo Finance stock data service
# @SPEC Yahoo Finance integration for real-time stock prices

"""Stock data service using yfinance with in-memory caching."""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


@dataclass
class StockData:
    """Stock data fetched from Yahoo Finance."""

    current_price: float
    change_percent: float
    currency: str
    market_cap: Optional[int]


# Simple in-memory cache: ticker -> (timestamp, StockData)
_cache: dict[str, tuple[float, StockData]] = {}


def _is_cache_valid(ticker: str) -> bool:
    """Check if cached data for the ticker is still within TTL."""
    if ticker not in _cache:
        return False
    cached_time, _ = _cache[ticker]
    return (time.time() - cached_time) < CACHE_TTL_SECONDS


def fetch_stock_data(ticker: str) -> Optional[StockData]:
    """
    Fetch stock data for a given ticker symbol.

    Returns StockData on success, None if the ticker is invalid or API fails.
    Results are cached in memory for 15 minutes.

    Layer 2: Domain validation - ticker must be non-empty
    Layer 4: Structured logging for traceability
    """
    if not ticker or not ticker.strip():
        return None

    ticker = ticker.strip().upper()

    # Check cache first
    if _is_cache_valid(ticker):
        _, cached_data = _cache[ticker]
        logger.debug("Cache hit for ticker %s", ticker)
        return cached_data

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # yfinance returns an empty-ish dict or a dict with "trailingPegRatio"
        # but no "currentPrice" for invalid tickers
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price is None:
            logger.warning("No price data found for ticker %s", ticker)
            return None

        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change_percent = 0.0
        if previous_close and previous_close > 0:
            change_percent = round(
                ((current_price - previous_close) / previous_close) * 100, 2
            )

        currency = info.get("currency", "USD")
        market_cap = info.get("marketCap")

        data = StockData(
            current_price=round(current_price, 2),
            change_percent=change_percent,
            currency=currency,
            market_cap=market_cap,
        )

        # Store in cache
        _cache[ticker] = (time.time(), data)
        logger.info(
            "Fetched stock data for %s: price=%.2f, change=%.2f%%",
            ticker,
            data.current_price,
            data.change_percent,
        )
        return data

    except Exception:
        logger.exception("Failed to fetch stock data for ticker %s", ticker)
        return None


def clear_cache() -> None:
    """Clear the stock data cache. Useful for testing."""
    _cache.clear()
