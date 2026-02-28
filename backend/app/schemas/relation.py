# @TASK P2-R3-T1 - CompanyRelation Pydantic schemas
# @SPEC docs/planning/02-trd.md#relations-api

from typing import Optional

from pydantic import BaseModel


class RelationResponse(BaseModel):
    """Response body for a single company relation."""

    id: int
    source_id: int
    target_id: int
    relation_type: str
    strength: Optional[float] = None

    model_config = {"from_attributes": True}


class RelationListResponse(BaseModel):
    """Response body for relation list endpoint."""

    items: list[RelationResponse]
    count: int
