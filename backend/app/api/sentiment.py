# @TASK SENT-1 - Sentiment analysis API endpoints
# @SPEC docs/planning/02-trd.md#sentiment-analysis

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.user import User
from app.services.sentiment_service import get_company_sentiment, analyze_news_sentiment

router = APIRouter()


@router.get("/companies/{company_id}/sentiment")
def get_sentiment(
    company_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get sentiment analysis for a company's news."""
    return get_company_sentiment(session, company_id)


@router.post("/sentiment/analyze")
def run_sentiment_analysis(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Trigger sentiment analysis for unanalyzed news items."""
    count = analyze_news_sentiment(session)
    return {"analyzed": count}
