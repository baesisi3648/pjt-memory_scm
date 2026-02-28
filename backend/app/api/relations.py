# @TASK P2-R3-T1 - Company Relations resource API
# @SPEC docs/planning/02-trd.md#relations-api
# @TEST tests/test_relations.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, or_, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.company import Company
from app.models.company_relation import CompanyRelation
from app.models.user import User
from app.schemas.relation import (
    CompanyRelationDetail,
    CompanyRelationListResponse,
    RelationListResponse,
    RelationResponse,
)

router = APIRouter()


# @TASK P2-R3-T1.1 - List all relations endpoint
@router.get("", response_model=RelationListResponse)
def list_relations(
    company_ids: Optional[str] = Query(
        default=None,
        description="Comma-separated company IDs; filters where source_id OR target_id in list",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> RelationListResponse:
    """
    List all company relations with optional company_ids filter.

    When company_ids is provided, returns relations where source_id OR target_id
    is in the given list.

    Layer 1: Input validation via FastAPI Query parameters
    Layer 2: Domain filtering (company_ids)
    Layer 4: Structured response with count
    """
    statement = select(CompanyRelation)

    if company_ids is not None:
        try:
            id_list = [int(x.strip()) for x in company_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="company_ids must be comma-separated integers",
            )
        if id_list:
            statement = statement.where(
                or_(
                    CompanyRelation.source_id.in_(id_list),
                    CompanyRelation.target_id.in_(id_list),
                )
            )

    relations = session.exec(statement).all()
    return RelationListResponse(
        items=[RelationResponse.model_validate(r) for r in relations],
        count=len(relations),
    )


# @TASK P2-R3-T1.2 - Relations for a specific company
# NOTE: This is mounted under /api/v1/companies prefix via main.py,
#       but we define a separate router for company-specific relations.
#       The actual endpoint path is /api/v1/companies/{company_id}/relations

company_relations_router = APIRouter()


@company_relations_router.get(
    "/{company_id}/relations", response_model=CompanyRelationListResponse
)
def get_company_relations(
    company_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CompanyRelationListResponse:
    """
    Get enriched relations for a specific company.

    Returns partner company name (Korean preferred) and direction
    (upstream = this company is the target, downstream = this company is the source).
    """
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found",
        )

    relations = session.exec(
        select(CompanyRelation).where(
            or_(
                CompanyRelation.source_id == company_id,
                CompanyRelation.target_id == company_id,
            )
        )
    ).all()

    # Prefetch all partner companies in a single query (avoid N+1)
    partner_ids = set()
    for rel in relations:
        partner_ids.add(rel.target_id if rel.source_id == company_id else rel.source_id)
    partners = {
        c.id: c
        for c in session.exec(select(Company).where(Company.id.in_(partner_ids))).all()
    } if partner_ids else {}

    enriched: list[CompanyRelationDetail] = []
    for rel in relations:
        if rel.source_id == company_id:
            partner = partners.get(rel.target_id)
            direction = "downstream"
        else:
            partner = partners.get(rel.source_id)
            direction = "upstream"

        partner_name = (partner.name_kr or partner.name) if partner else "Unknown"

        enriched.append(CompanyRelationDetail(
            id=rel.id,
            company_id=partner.id if partner else 0,
            company_name=partner_name,
            relation_type=rel.relation_type or "supplier",
            strength=rel.strength,
            direction=direction,
        ))

    return CompanyRelationListResponse(items=enriched, count=len(enriched))
