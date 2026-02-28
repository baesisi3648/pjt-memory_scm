# @TASK P2-R2-T1 - Clusters resource API
# @SPEC docs/planning/02-trd.md#clusters-api
# @TEST tests/test_clusters.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.cluster import Cluster
from app.models.company import Company
from app.models.user import User
from app.schemas.cluster import ClusterListResponse, ClusterResponse
from app.schemas.company import CompanyListResponse, CompanyResponse

router = APIRouter()


# @TASK P2-R2-T1.1 - List clusters endpoint
@router.get("", response_model=ClusterListResponse)
def list_clusters(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ClusterListResponse:
    """
    List all clusters including parent_id for hierarchy.

    Layer 4: Structured response with count
    """
    clusters = session.exec(select(Cluster)).all()
    return ClusterListResponse(
        items=[ClusterResponse.model_validate(c) for c in clusters],
        count=len(clusters),
    )


# @TASK P2-R2-T1.2 - List companies in a cluster
@router.get("/{cluster_id}/companies", response_model=CompanyListResponse)
def list_cluster_companies(
    cluster_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CompanyListResponse:
    """
    List all companies belonging to a specific cluster.

    Returns 404 if cluster not found.
    """
    cluster = session.get(Cluster, cluster_id)
    if cluster is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster with id {cluster_id} not found",
        )

    companies = session.exec(
        select(Company).where(Company.cluster_id == cluster_id)
    ).all()
    return CompanyListResponse(
        items=[CompanyResponse.model_validate(c) for c in companies],
        count=len(companies),
    )
