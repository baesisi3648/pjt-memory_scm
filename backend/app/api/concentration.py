# @TASK HHI-T1 - Concentration index API endpoint
# @SPEC docs/planning/02-trd.md#analytics-api

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.user import User
from app.services.concentration_service import calculate_tier_hhi

router = APIRouter()


@router.get("/concentration")
def get_concentration_index(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get HHI concentration index per supply chain tier."""
    return calculate_tier_hhi(session)
