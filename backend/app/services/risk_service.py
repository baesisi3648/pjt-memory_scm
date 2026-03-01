# @TASK RISK-1 - Company risk score calculation service
# @SPEC docs/planning/02-trd.md#risk-score-api
"""Company risk score calculation service."""
import logging

from sqlmodel import Session, select, func

from app.models.alert import Alert
from app.models.company_relation import CompanyRelation

logger = logging.getLogger(__name__)

# Severity weights for risk calculation
SEVERITY_WEIGHTS = {
    "critical": 30,
    "warning": 15,
    "info": 5,
}


def calculate_risk_score(session: Session, company_id: int) -> dict:
    """Calculate composite risk score for a company (0-100).

    Components:
    - alert_score: based on active alerts count and severity (0-50)
    - concentration_score: supply chain dependency concentration (0-30)
    - connectivity_score: how connected/exposed the company is (0-20)
    """
    # 1. Alert score (0-50)
    alerts = session.exec(
        select(Alert)
        .where(Alert.company_id == company_id)
        .where(Alert.is_read == False)  # noqa: E712
    ).all()

    alert_points = sum(SEVERITY_WEIGHTS.get(a.severity, 0) for a in alerts)
    alert_score = min(alert_points, 50)  # cap at 50

    # 2. Concentration score (0-30) - how dependent on single suppliers/customers
    # Count unique suppliers and customers
    as_target = session.exec(
        select(func.count(func.distinct(CompanyRelation.source_id)))
        .where(CompanyRelation.target_id == company_id)
    ).one()
    as_source = session.exec(
        select(func.count(func.distinct(CompanyRelation.target_id)))
        .where(CompanyRelation.source_id == company_id)
    ).one()

    supplier_count = as_target or 0
    customer_count = as_source or 0
    total_partners = supplier_count + customer_count

    # Fewer partners = higher concentration risk
    if total_partners == 0:
        concentration_score = 30
    elif total_partners <= 2:
        concentration_score = 20
    elif total_partners <= 5:
        concentration_score = 10
    else:
        concentration_score = 5

    # 3. Connectivity score (0-20) - more connections = more exposure
    connectivity_score = min(total_partners * 2, 20)

    total = alert_score + concentration_score + connectivity_score

    # Determine risk level
    if total >= 60:
        level = "critical"
    elif total >= 40:
        level = "high"
    elif total >= 20:
        level = "medium"
    else:
        level = "low"

    return {
        "score": min(total, 100),
        "level": level,
        "breakdown": {
            "alert_score": alert_score,
            "concentration_score": concentration_score,
            "connectivity_score": connectivity_score,
        },
        "details": {
            "active_alerts": len(alerts),
            "supplier_count": supplier_count,
            "customer_count": customer_count,
        },
    }


def calculate_all_risk_scores(session: Session) -> list[dict]:
    """Calculate risk scores for all companies."""
    from app.models.company import Company

    companies = session.exec(select(Company)).all()
    results = []
    for company in companies:
        score_data = calculate_risk_score(session, company.id)
        results.append({
            "company_id": company.id,
            "company_name": company.name,
            **score_data,
        })
    # Sort by score descending (highest risk first)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
