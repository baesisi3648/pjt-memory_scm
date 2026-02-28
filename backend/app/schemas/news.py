# @TASK P2-R5-T1 - NewsItem Pydantic schemas
# @SPEC docs/planning/02-trd.md#news-api

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsItemResponse(BaseModel):
    """Response body for news item endpoints."""

    id: int
    title: str
    url: str
    source: Optional[str] = None
    company_id: Optional[int] = None
    published_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
