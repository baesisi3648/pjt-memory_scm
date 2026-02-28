# @TASK P2-R6-T1 - User Filters Pydantic schemas
# @SPEC docs/planning/02-trd.md#user-filters-api

from pydantic import BaseModel


class FilterCreateRequest(BaseModel):
    """Request body for POST /api/v1/filters."""

    name: str
    company_ids: list[int]
    is_default: bool = False


class FilterResponse(BaseModel):
    """Response body for user filter endpoints."""

    id: int
    user_id: int
    name: str
    company_ids: list[int]
    is_default: bool

    model_config = {"from_attributes": True}
