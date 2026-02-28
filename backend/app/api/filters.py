# @TASK P2-R6-T1 - User Filters CRUD API
# @SPEC docs/planning/02-trd.md#user-filters-api
# @TEST tests/test_filters.py

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_filter import UserFilter
from app.schemas.filters import FilterCreateRequest, FilterResponse

router = APIRouter()


def _to_response(f: UserFilter) -> FilterResponse:
    """Convert a UserFilter ORM instance to a FilterResponse with parsed company_ids."""
    return FilterResponse(
        id=f.id,
        user_id=f.user_id,
        name=f.name,
        company_ids=json.loads(f.company_ids),
        is_default=f.is_default,
    )


# @TASK P2-R6-T1.1 - List current user's filters
@router.get("", response_model=list[FilterResponse])
def list_filters(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[FilterResponse]:
    """
    Return all saved filters belonging to the authenticated user.

    Layer 1: Auth via get_current_user dependency
    Layer 2: Scoped to current user's filters only
    """
    filters = session.exec(
        select(UserFilter).where(UserFilter.user_id == current_user.id)
    ).all()
    return [_to_response(f) for f in filters]


# @TASK P2-R6-T1.2 - Create a new filter
@router.post("", response_model=FilterResponse, status_code=status.HTTP_201_CREATED)
def create_filter(
    request: FilterCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FilterResponse:
    """
    Create a new filter preset for the authenticated user.

    Layer 1: Input validation via Pydantic (FilterCreateRequest)
    Layer 2: user_id set from authenticated user (not from request body)
    """
    user_filter = UserFilter(
        user_id=current_user.id,
        name=request.name,
        company_ids=json.dumps(request.company_ids),
        is_default=request.is_default,
    )
    session.add(user_filter)
    session.commit()
    session.refresh(user_filter)
    return _to_response(user_filter)


# @TASK P2-R6-T1.3 - Delete a filter (ownership check)
@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filter(
    filter_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """
    Delete a filter preset. Only the owner can delete their own filters.

    Layer 1: Auth via get_current_user dependency
    Layer 2: Ownership validation (403 if not owner)
    """
    user_filter = session.get(UserFilter, filter_id)
    if user_filter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found",
        )
    if user_filter.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this filter",
        )
    session.delete(user_filter)
    session.commit()
