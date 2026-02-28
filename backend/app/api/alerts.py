# @TASK P2-R4-T1 - Alerts resource API endpoints
# @SPEC docs/planning/02-trd.md#alerts-api
# @TEST tests/test_alerts.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertResponse

router = APIRouter()


# @TASK P2-R4-T1.1 - List alerts with optional filters
@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    severity: Optional[str] = Query(default=None, description="Filter by severity: critical, warning, info"),
    is_read: Optional[bool] = Query(default=None, description="Filter by read status"),
    company_id: Optional[int] = Query(default=None, description="Filter by company ID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Alert]:
    """
    List all alerts with optional filters.

    Layer 1: Input validation via FastAPI query params
    Layer 2: Domain filtering (severity, is_read, company_id)
    Layer 4: Ordered by created_at descending
    """
    statement = select(Alert)

    if severity is not None:
        statement = statement.where(Alert.severity == severity)
    if is_read is not None:
        statement = statement.where(Alert.is_read == is_read)
    if company_id is not None:
        statement = statement.where(Alert.company_id == company_id)

    statement = statement.order_by(Alert.created_at.desc())
    alerts = session.exec(statement).all()
    return alerts


# @TASK P2-R4-T1.2 - Mark alert as read
@router.patch("/alerts/{alert_id}/read", response_model=AlertResponse)
def mark_alert_as_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Alert:
    """
    Mark a specific alert as read.

    Layer 1: Path param validation (alert_id: int)
    Layer 2: Domain validation (alert must exist)
    Layer 4: Returns updated alert
    """
    alert = session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    alert.is_read = True
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


# @TASK P2-R4-T1.3 - Company-specific alerts
@router.get("/companies/{company_id}/alerts", response_model=list[AlertResponse])
def list_company_alerts(
    company_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Alert]:
    """
    List alerts for a specific company.

    Layer 1: Path param validation (company_id: int)
    Layer 4: Ordered by created_at descending
    """
    statement = (
        select(Alert)
        .where(Alert.company_id == company_id)
        .order_by(Alert.created_at.desc())
    )
    alerts = session.exec(statement).all()
    return alerts
