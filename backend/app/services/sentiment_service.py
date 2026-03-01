# @TASK SENT-1 - News sentiment analysis using TextBlob
# @SPEC docs/planning/02-trd.md#sentiment-analysis

"""News sentiment analysis using TextBlob."""
import logging
from textblob import TextBlob
from sqlmodel import Session, select

from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)


def analyze_sentiment(text: str) -> float:
    """Analyze sentiment of text. Returns polarity (-1.0 to 1.0)."""
    if not text:
        return 0.0
    blob = TextBlob(text)
    return round(blob.sentiment.polarity, 3)


def analyze_news_sentiment(session: Session, limit: int = 50) -> int:
    """Analyze sentiment for news items that haven't been analyzed yet.
    Returns count of analyzed items."""
    unanalyzed = session.exec(
        select(NewsItem)
        .where(NewsItem.sentiment == None)  # noqa: E711
        .limit(limit)
    ).all()

    count = 0
    for item in unanalyzed:
        try:
            item.sentiment = analyze_sentiment(item.title)
            session.add(item)
            count += 1
        except Exception as e:
            logger.error("Sentiment analysis failed for news %d: %s", item.id, e)

    if count > 0:
        session.commit()
        logger.info("Analyzed sentiment for %d news items", count)

    return count


def get_company_sentiment(session: Session, company_id: int) -> dict:
    """Get average sentiment for a company's news."""
    from sqlmodel import func

    result = session.exec(
        select(
            func.avg(NewsItem.sentiment),
            func.count(NewsItem.id),
        )
        .where(NewsItem.company_id == company_id)
        .where(NewsItem.sentiment != None)  # noqa: E711
    ).first()

    avg_sentiment = result[0] if result and result[0] is not None else 0.0
    count = result[1] if result else 0

    if avg_sentiment > 0.1:
        label = "positive"
    elif avg_sentiment < -0.1:
        label = "negative"
    else:
        label = "neutral"

    return {
        "average_sentiment": round(float(avg_sentiment), 3),
        "label": label,
        "analyzed_count": count,
    }
