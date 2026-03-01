# @TASK P2-R4-T1 - Alert Pydantic schemas
# @SPEC docs/planning/02-trd.md#alerts-api

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlertResponse(BaseModel):
    """Response body for alert endpoints."""

    id: int
    company_id: Optional[int] = None
    severity: str
    title: str
    description: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Paginated response body for alert list endpoint."""

    items: list[AlertResponse]
    count: int
