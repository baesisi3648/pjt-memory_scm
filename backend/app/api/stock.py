# @TASK STOCK-T2 - Stock data API endpoint
# @SPEC GET /api/v1/companies/{id}/stock
# @TEST tests/test_stock.py

"""Stock data endpoint for company stock price information."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.company import Company
from app.models.user import User
from app.services.stock_service import fetch_stock_data

router = APIRouter()


class StockResponse(BaseModel):
    """Response body for stock data endpoint."""

    ticker: Optional[str] = None
    price: Optional[float] = None
    change_percent: Optional[float] = None
    currency: Optional[str] = None
    market_cap: Optional[int] = None
    updated_at: Optional[str] = None


@router.get("/{company_id}/stock", response_model=StockResponse)
def get_company_stock(
    company_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StockResponse:
    """
    Get stock data for a company.

    Returns stock price, change percentage, currency, and market cap.
    Returns 404 if the company is not found.
    Returns { ticker: null } if the company has no ticker symbol.

    Layer 1: Input validation via FastAPI path parameter
    Layer 2: Company existence check
    Layer 4: Structured response with timestamp
    """
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found",
        )

    if not company.ticker:
        return StockResponse(ticker=None)

    stock_data = fetch_stock_data(company.ticker)

    if stock_data is None:
        # Ticker exists but API call failed or returned no data
        return StockResponse(
            ticker=company.ticker,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    return StockResponse(
        ticker=company.ticker,
        price=stock_data.current_price,
        change_percent=stock_data.change_percent,
        currency=stock_data.currency,
        market_cap=stock_data.market_cap,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
