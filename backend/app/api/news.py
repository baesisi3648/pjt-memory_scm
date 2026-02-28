# @TASK P2-R5-T1 - News items resource API endpoints
# @SPEC docs/planning/02-trd.md#news-api

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.company import Company
from app.models.news_item import NewsItem
from app.models.user import User
from app.schemas.news import NewsItemResponse
from app.services.news_service import fetch_company_news

router = APIRouter()


@router.get("/companies/{company_id}/news", response_model=list[NewsItemResponse])
async def list_company_news(
    company_id: int,
    limit: int = Query(default=10, ge=1, le=100, description="Max number of news items to return"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[NewsItem]:
    """
    List news items for a specific company.
    Fetches from NewsAPI.org if API key is configured and cache is stale.
    Falls back to DB-only data otherwise.
    """
    # Look up company name for NewsAPI query (optional — gracefully degrades)
    company = session.get(Company, company_id)
    company_name = company.name if company else ""

    news_items = await fetch_company_news(
        session=session,
        company_id=company_id,
        company_name=company_name,
        limit=limit,
    )
    return news_items
