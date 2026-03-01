# @TASK P2-R7-T1 - Alert Rules CRUD API
# @SPEC docs/planning/02-trd.md#alert-rules-api
# @TEST tests/test_alert_rules.py

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.alert_rule import AlertRule
from app.models.user import User
from app.schemas.alert_rules import (
    AlertRuleCreateRequest,
    AlertRuleListResponse,
    AlertRuleResponse,
    AlertRuleUpdateRequest,
)

router = APIRouter()


def _to_response(rule: AlertRule) -> AlertRuleResponse:
    """Convert an AlertRule ORM instance to a response with parsed condition."""
    return AlertRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.name,
        condition=json.loads(rule.condition),
        is_active=rule.is_active,
    )


def _get_owned_rule(
    rule_id: int,
    current_user: User,
    session: Session,
) -> AlertRule:
    """Fetch an alert rule and verify ownership. Raises 404/403 on failure."""
    rule = session.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )
    if rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this alert rule",
        )
    return rule


# @TASK P2-R7-T1.1 - List current user's alert rules
@router.get("", response_model=AlertRuleListResponse)
def list_alert_rules(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlertRuleListResponse:
    """
    Return all alert rules belonging to the authenticated user, with pagination.

    Layer 1: Auth via get_current_user dependency
    Layer 2: Scoped to current user's rules only
    Layer 4: Structured response with total count and paginated items
    """
    statement = select(AlertRule).where(AlertRule.user_id == current_user.id)

    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    rules = session.exec(statement.offset(skip).limit(limit)).all()
    return AlertRuleListResponse(
        items=[_to_response(r) for r in rules],
        count=total,
    )


# @TASK P2-R7-T1.2 - Create a new alert rule
@router.post("", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    request: AlertRuleCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlertRuleResponse:
    """
    Create a new alert rule for the authenticated user.

    Layer 1: Input validation via Pydantic (AlertRuleCreateRequest)
    Layer 2: user_id set from authenticated user (not from request body)
    """
    rule = AlertRule(
        user_id=current_user.id,
        name=request.name,
        condition=json.dumps(request.condition),
        is_active=True,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return _to_response(rule)


# @TASK P2-R7-T1.3 - Update an alert rule (ownership check)
@router.put("/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: int,
    request: AlertRuleUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlertRuleResponse:
    """
    Update an existing alert rule. Only the owner can update their rules.

    Layer 1: Auth + input validation via Pydantic
    Layer 2: Ownership validation (403 if not owner)
    """
    rule = _get_owned_rule(rule_id, current_user, session)
    rule.name = request.name
    rule.condition = json.dumps(request.condition)
    rule.is_active = request.is_active
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return _to_response(rule)


# @TASK P2-R7-T1.4 - Toggle alert rule active status
@router.patch("/{rule_id}/toggle", response_model=AlertRuleResponse)
def toggle_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlertRuleResponse:
    """
    Toggle the is_active flag on an alert rule. Only the owner can toggle.

    Layer 2: Ownership validation (403 if not owner)
    """
    rule = _get_owned_rule(rule_id, current_user, session)
    rule.is_active = not rule.is_active
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return _to_response(rule)


# @TASK P2-R7-T1.5 - Delete an alert rule (ownership check)
@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """
    Delete an alert rule. Only the owner can delete their rules.

    Layer 1: Auth via get_current_user dependency
    Layer 2: Ownership validation (403 if not owner)
    """
    rule = _get_owned_rule(rule_id, current_user, session)
    session.delete(rule)
    session.commit()
