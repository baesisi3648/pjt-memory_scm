# @TASK P2-R1-T1 - Companies resource API
# @SPEC docs/planning/02-trd.md#companies-api
# @TEST tests/test_companies.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyListResponse, CompanyResponse

router = APIRouter()


# @TASK P2-R1-T1.1 - List companies endpoint
@router.get("", response_model=CompanyListResponse)
def list_companies(
    cluster_id: Optional[int] = Query(default=None, description="Filter by cluster ID"),
    tier: Optional[str] = Query(default=None, description="Filter by tier"),
    company_ids: Optional[str] = Query(
        default=None,
        description="Comma-separated list of company IDs to filter",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CompanyListResponse:
    """
    List companies with optional filters.

    Layer 1: Input validation via FastAPI Query parameters
    Layer 2: Domain filtering (cluster_id, tier, company_ids)
    Layer 4: Structured response with count
    """
    statement = select(Company)

    if cluster_id is not None:
        statement = statement.where(Company.cluster_id == cluster_id)

    if tier is not None:
        statement = statement.where(Company.tier == tier)

    if company_ids is not None:
        try:
            id_list = [int(x.strip()) for x in company_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="company_ids must be comma-separated integers",
            )
        if id_list:
            statement = statement.where(Company.id.in_(id_list))

    companies = session.exec(statement).all()
    return CompanyListResponse(
        items=[CompanyResponse.model_validate(c) for c in companies],
        count=len(companies),
    )


# @TASK P2-R1-T1.2 - Get company detail endpoint
@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    """
    Get a single company by ID.

    Returns 404 if not found.
    """
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found",
        )
    return company
