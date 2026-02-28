# @TASK P2-R5-T1 - News items resource API endpoints
# @SPEC docs/planning/02-trd.md#news-api
# @TEST tests/test_news.py

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.news_item import NewsItem
from app.models.user import User
from app.schemas.news import NewsItemResponse

router = APIRouter()


# @TASK P2-R5-T1.1 - Company news list
@router.get("/companies/{company_id}/news", response_model=list[NewsItemResponse])
def list_company_news(
    company_id: int,
    limit: int = Query(default=10, ge=1, le=100, description="Max number of news items to return"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[NewsItem]:
    """
    List news items for a specific company, ordered by published_at descending.

    Layer 1: Input validation via FastAPI query params (limit: 1-100)
    Layer 2: Scoped to company_id
    Layer 4: Ordered by published_at descending, limited to requested count
    """
    statement = (
        select(NewsItem)
        .where(NewsItem.company_id == company_id)
        .order_by(NewsItem.published_at.desc())
        .limit(limit)
    )
    news_items = session.exec(statement).all()
    return news_items
