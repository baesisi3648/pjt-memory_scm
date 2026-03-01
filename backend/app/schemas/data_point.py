# @TASK DATA-POINTS-T1 - DataPoint Pydantic schemas
# @SPEC docs/planning/02-trd.md#data-points-api

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DataPointResponse(BaseModel):
    """Response body for data point endpoints."""

    id: int
    source_id: int
    company_id: Optional[int] = None
    metric: str
    value: float
    unit: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class DataPointListResponse(BaseModel):
    """Paginated response body for data point list endpoint."""

    items: list[DataPointResponse]
    count: int
