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


class CompanyRelationDetail(BaseModel):
    """Enriched relation for a specific company's perspective."""

    id: int
    company_id: int
    company_name: str
    relation_type: str
    strength: Optional[float] = None
    direction: str  # 'upstream' | 'downstream'


class CompanyRelationListResponse(BaseModel):
    """Response body for company-specific enriched relations."""

    items: list[CompanyRelationDetail]
    count: int
