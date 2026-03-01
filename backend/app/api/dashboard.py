# @TASK PERF-2 - Unified dashboard API endpoint
# @SPEC Reduces frontend API calls from 4 to 1 by combining
#       companies, clusters, relations, and unread alerts.
# @TEST tests/test_dashboard.py

import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.cache import get_cached, make_cache_key, set_cached
from app.core.database import get_session
from app.core.security import get_current_user
from app.models.alert import Alert
from app.models.cluster import Cluster
from app.models.company import Company
from app.models.company_relation import CompanyRelation
from app.models.user import User
from app.schemas.alert import AlertResponse
from app.schemas.cluster import ClusterResponse
from app.schemas.company import CompanyResponse
from app.schemas.dashboard import DashboardResponse
from app.schemas.relation import RelationResponse

logger = logging.getLogger(__name__)

router = APIRouter()

CACHE_PREFIX = "dashboard"


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DashboardResponse:
    """Single endpoint that returns all data needed for the main dashboard graph.

    Aggregates companies, clusters, company relations, and unread alerts
    into a single response so the frontend only needs one API call.

    Layer 1: Authentication via get_current_user dependency
    Layer 2: No additional domain validation needed (read-only aggregate)
    Layer 4: Structured response with typed schema, cached for 5 minutes
    """
    cache_key = make_cache_key(CACHE_PREFIX)
    cached = get_cached(cache_key)
    if cached is not None:
        logger.debug("Dashboard cache hit (key=%s)", cache_key)
        return cached

    companies = session.exec(select(Company)).all()
    clusters = session.exec(select(Cluster)).all()
    relations = session.exec(select(CompanyRelation)).all()
    alerts = session.exec(
        select(Alert)
        .where(Alert.is_read == False)  # noqa: E712
        .order_by(Alert.created_at.desc())
    ).all()

    response = DashboardResponse(
        companies=[CompanyResponse.model_validate(c) for c in companies],
        clusters=[ClusterResponse.model_validate(c) for c in clusters],
        relations=[RelationResponse.model_validate(r) for r in relations],
        alerts=[AlertResponse.model_validate(a) for a in alerts],
    )

    set_cached(cache_key, response)
    logger.debug("Dashboard cache miss, stored (key=%s)", cache_key)

    return response
