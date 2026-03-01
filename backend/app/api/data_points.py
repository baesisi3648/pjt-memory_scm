# @TASK DATA-POINTS-T2 - DataPoint resource API endpoints
# @SPEC docs/planning/02-trd.md#data-points-api
# @TEST tests/test_data_points.py

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.data_point import DataPoint
from app.models.user import User
from app.schemas.data_point import DataPointListResponse, DataPointResponse

router = APIRouter()


# @TASK DATA-POINTS-T2.1 - List data points for a company with filters
@router.get("/{company_id}/data-points", response_model=DataPointListResponse)
def list_company_data_points(
    company_id: int,
    metric: Optional[str] = Query(default=None, description="Filter by metric name"),
    from_date: Optional[datetime] = Query(default=None, description="Filter data points from this date"),
    to_date: Optional[datetime] = Query(default=None, description="Filter data points up to this date"),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DataPointListResponse:
    """
    List data points for a specific company with optional filters and pagination.

    Layer 1: Input validation via FastAPI query params (metric, from_date, to_date, skip, limit)
    Layer 2: Domain filtering (company_id, metric, date range)
    Layer 4: Ordered by timestamp descending, structured response with total count
    """
    statement = select(DataPoint).where(DataPoint.company_id == company_id)

    if metric is not None:
        statement = statement.where(DataPoint.metric == metric)
    if from_date is not None:
        statement = statement.where(DataPoint.timestamp >= from_date)
    if to_date is not None:
        statement = statement.where(DataPoint.timestamp <= to_date)

    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    statement = statement.order_by(DataPoint.timestamp.desc())
    data_points = session.exec(statement.offset(skip).limit(limit)).all()

    return DataPointListResponse(
        items=[DataPointResponse.model_validate(dp) for dp in data_points],
        count=total,
    )
