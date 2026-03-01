# @TASK RISK-1 - Risk score API endpoints
# @SPEC docs/planning/02-trd.md#risk-score-api
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.user import User
from app.services.risk_service import calculate_all_risk_scores, calculate_risk_score

router = APIRouter()


@router.get("/risk-scores")
def get_all_risk_scores(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get risk scores for all companies, sorted by highest risk."""
    return calculate_all_risk_scores(session)


@router.get("/companies/{company_id}/risk")
def get_company_risk(
    company_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get risk score for a specific company."""
    return calculate_risk_score(session, company_id)
