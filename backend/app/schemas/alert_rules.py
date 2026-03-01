# @TASK P2-R7-T1 - Alert Rules Pydantic schemas
# @SPEC docs/planning/02-trd.md#alert-rules-api

from typing import Any

from pydantic import BaseModel


class AlertRuleCreateRequest(BaseModel):
    """Request body for POST /api/v1/alert-rules."""

    name: str
    condition: dict[str, Any]


class AlertRuleUpdateRequest(BaseModel):
    """Request body for PUT /api/v1/alert-rules/{id}."""

    name: str
    condition: dict[str, Any]
    is_active: bool


class AlertRuleResponse(BaseModel):
    """Response body for alert rule endpoints."""

    id: int
    user_id: int
    name: str
    condition: dict[str, Any]
    is_active: bool

    model_config = {"from_attributes": True}


class AlertRuleListResponse(BaseModel):
    """Paginated response body for alert rule list endpoint."""

    items: list[AlertRuleResponse]
    count: int
