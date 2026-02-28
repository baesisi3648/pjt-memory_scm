# @TASK P2-R2-T1 - Cluster Pydantic schemas
# @SPEC docs/planning/02-trd.md#clusters-api

from typing import Optional

from pydantic import BaseModel


class ClusterResponse(BaseModel):
    """Response body for a single cluster."""

    id: int
    name: str
    parent_id: Optional[int] = None
    tier: str

    model_config = {"from_attributes": True}


class ClusterListResponse(BaseModel):
    """Response body for cluster list endpoint."""

    items: list[ClusterResponse]
    count: int
