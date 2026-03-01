# @TASK P0-T0.3 - Database schema: NewsItem model
# @SPEC docs/planning/04-database-design.md#news_items

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class NewsItem(SQLModel, table=True):
    """
    News item model representing news related to companies.
    """

    __tablename__ = "news_items"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    title: str = Field(max_length=500)
    url: str = Field(max_length=1000)
    source: Optional[str] = Field(default=None, max_length=255)
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True)
    published_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sentiment: Optional[float] = Field(default=None)

    # Relationships
    company: Optional["Company"] = Relationship(back_populates="news_items")
