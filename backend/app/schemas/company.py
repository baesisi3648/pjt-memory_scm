# @TASK P2-R1-T1 - Company Pydantic schemas
# @SPEC docs/planning/02-trd.md#companies-api

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CompanyResponse(BaseModel):
    """Response body for a single company."""

    id: int
    name: str
    name_kr: Optional[str] = None
    cluster_id: Optional[int] = None
    tier: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyListResponse(BaseModel):
    """Response body for company list endpoint."""

    items: list[CompanyResponse]
    count: int
