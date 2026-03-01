# @TASK EXCHANGE-T2 - Exchange rate API endpoint
# @SPEC GET /api/v1/exchange-rates
# @TEST tests/test_exchange.py

"""Exchange rate endpoint returning USD-based rates from frankfurter.app."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user import User
from app.services.exchange_service import BASE_CURRENCY, fetch_exchange_rates

router = APIRouter()


class ExchangeRatesResponse(BaseModel):
    """Response body for the exchange rates endpoint."""

    base: str
    rates: dict[str, float]
    updated_at: str


@router.get("/exchange-rates", response_model=ExchangeRatesResponse)
def get_exchange_rates(
    current_user: User = Depends(get_current_user),
) -> ExchangeRatesResponse:
    """
    Get the latest USD-based exchange rates.

    Returns rates for KRW, JPY, TWD, and EUR relative to USD.
    Data is cached for 30 minutes; a fresh API call is made only when
    the cache has expired.

    Layer 1: Auth enforced via get_current_user dependency
    Layer 2: API response validated before caching in exchange_service
    Layer 4: Structured response with UTC timestamp
    """
    rates = fetch_exchange_rates()

    if rates is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Exchange rate data is temporarily unavailable. Please try again later.",
        )

    return ExchangeRatesResponse(
        base=BASE_CURRENCY,
        rates=rates,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
