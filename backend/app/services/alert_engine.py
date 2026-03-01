# @TASK T-ALERT-ENGINE - Alert evaluation engine
# @SPEC Evaluates AlertRules against DataPoints and generates Alerts
# @TEST tests/test_alert_engine.py
"""
Alert evaluation engine.

Periodically evaluates all active AlertRules against recent DataPoints
and NewsItems. When a condition is met and no duplicate alert exists
within the last 24 hours, a new Alert is created.

Condition JSON format (stored in AlertRule.condition as a string):
{
    "rule_type": "price_change" | "lead_time" | "news_detect" | "inventory_change",
    "company_id": <int>,            # which company to evaluate
    "threshold": <float>,           # numeric threshold (meaning depends on rule_type)
    "direction": "drop" | "rise",   # for price_change / inventory_change
    "unit": "days",                 # for lead_time
    "min_articles": <int>,          # for news_detect
    "sentiment_below": <float>      # for news_detect
}
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.data_point import DataPoint
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DUPLICATE_WINDOW_HOURS = 24
RECENT_DATA_HOURS = 48  # How far back to look for DataPoints
RECENT_NEWS_HOURS = 24  # How far back to look for NewsItems

SEVERITY_MAP: dict[str, str] = {
    "price_change": "warning",
    "lead_time": "critical",
    "news_detect": "warning",
    "inventory_change": "critical",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EvaluationResult:
    """Result of a single rule evaluation."""

    triggered: bool
    message: str


# ---------------------------------------------------------------------------
# Individual evaluators
# ---------------------------------------------------------------------------

def _evaluate_price_change(
    session: Session,
    company_id: int,
    condition: dict[str, Any],
) -> EvaluationResult:
    """
    Evaluate price_change rule.

    Triggers when the most recent price differs from the previous price
    by more than threshold %.

    Expected condition keys:
        threshold (float): percentage change to trigger (e.g. 5 = 5%)
        direction (str): "drop" or "rise"
    """
    threshold = condition.get("threshold")
    direction = condition.get("direction", "drop")

    if threshold is None:
        return EvaluationResult(False, "Missing 'threshold' in condition")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_DATA_HOURS)

    # Fetch the two most recent price DataPoints for this company
    statement = (
        select(DataPoint)
        .where(
            DataPoint.company_id == company_id,
            DataPoint.metric == "stock_price",
            DataPoint.timestamp >= cutoff,
        )
        .order_by(DataPoint.timestamp.desc())
        .limit(2)
    )
    points = session.exec(statement).all()

    if len(points) < 2:
        return EvaluationResult(
            False,
            f"Insufficient price data points (need 2, have {len(points)})",
        )

    latest_price = points[0].value
    previous_price = points[1].value

    if previous_price == 0:
        return EvaluationResult(False, "Previous price is zero, cannot compute change")

    pct_change = ((latest_price - previous_price) / abs(previous_price)) * 100

    if direction == "drop" and pct_change <= -threshold:
        return EvaluationResult(
            True,
            f"Price dropped {abs(pct_change):.1f}% "
            f"(from {previous_price:.2f} to {latest_price:.2f}), "
            f"exceeding {threshold}% threshold",
        )

    if direction == "rise" and pct_change >= threshold:
        return EvaluationResult(
            True,
            f"Price rose {pct_change:.1f}% "
            f"(from {previous_price:.2f} to {latest_price:.2f}), "
            f"exceeding {threshold}% threshold",
        )

    return EvaluationResult(
        False,
        f"Price change {pct_change:+.1f}% within threshold ({threshold}% {direction})",
    )


def _evaluate_lead_time(
    session: Session,
    company_id: int,
    condition: dict[str, Any],
) -> EvaluationResult:
    """
    Evaluate lead_time rule.

    Triggers when the most recent lead_time metric exceeds the threshold.

    Expected condition keys:
        threshold (float): max acceptable lead time (e.g. 30)
        unit (str): "days" (informational)
    """
    threshold = condition.get("threshold")
    unit = condition.get("unit", "days")

    if threshold is None:
        return EvaluationResult(False, "Missing 'threshold' in condition")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_DATA_HOURS)

    statement = (
        select(DataPoint)
        .where(
            DataPoint.company_id == company_id,
            DataPoint.metric == "lead_time",
            DataPoint.timestamp >= cutoff,
        )
        .order_by(DataPoint.timestamp.desc())
        .limit(1)
    )
    point = session.exec(statement).first()

    if point is None:
        return EvaluationResult(False, "No recent lead_time data available")

    if point.value > threshold:
        return EvaluationResult(
            True,
            f"Lead time {point.value:.0f} {unit} exceeds threshold of {threshold:.0f} {unit}",
        )

    return EvaluationResult(
        False,
        f"Lead time {point.value:.0f} {unit} within threshold ({threshold:.0f} {unit})",
    )


def _evaluate_news_detect(
    session: Session,
    company_id: int,
    condition: dict[str, Any],
) -> EvaluationResult:
    """
    Evaluate news_detect rule.

    Triggers when there are at least min_articles with sentiment
    below the sentiment_below threshold in the recent window.

    Expected condition keys:
        min_articles (int): minimum number of negative articles (e.g. 3)
        sentiment_below (float): sentiment threshold (e.g. -0.3)
    """
    min_articles = condition.get("min_articles", 3)
    sentiment_below = condition.get("sentiment_below", -0.3)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_NEWS_HOURS)

    statement = (
        select(NewsItem)
        .where(
            NewsItem.company_id == company_id,
            NewsItem.sentiment != None,  # noqa: E711
            NewsItem.sentiment < sentiment_below,
            NewsItem.published_at >= cutoff,
        )
    )
    negative_articles = session.exec(statement).all()
    count = len(negative_articles)

    if count >= min_articles:
        return EvaluationResult(
            True,
            f"Found {count} negative-sentiment articles "
            f"(sentiment < {sentiment_below}) in the last {RECENT_NEWS_HOURS}h, "
            f"threshold is {min_articles}",
        )

    return EvaluationResult(
        False,
        f"Found {count} negative articles, below threshold of {min_articles}",
    )


def _evaluate_inventory_change(
    session: Session,
    company_id: int,
    condition: dict[str, Any],
) -> EvaluationResult:
    """
    Evaluate inventory_change rule.

    Triggers when inventory level changes by more than threshold %
    compared to the previous reading.

    Expected condition keys:
        threshold (float): percentage change to trigger (e.g. 20 = 20%)
        direction (str): "decrease" or "increase"
    """
    threshold = condition.get("threshold")
    direction = condition.get("direction", "decrease")

    if threshold is None:
        return EvaluationResult(False, "Missing 'threshold' in condition")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_DATA_HOURS)

    statement = (
        select(DataPoint)
        .where(
            DataPoint.company_id == company_id,
            DataPoint.metric == "inventory",
            DataPoint.timestamp >= cutoff,
        )
        .order_by(DataPoint.timestamp.desc())
        .limit(2)
    )
    points = session.exec(statement).all()

    if len(points) < 2:
        return EvaluationResult(
            False,
            f"Insufficient inventory data points (need 2, have {len(points)})",
        )

    latest = points[0].value
    previous = points[1].value

    if previous == 0:
        return EvaluationResult(False, "Previous inventory is zero, cannot compute change")

    pct_change = ((latest - previous) / abs(previous)) * 100

    if direction == "decrease" and pct_change <= -threshold:
        return EvaluationResult(
            True,
            f"Inventory decreased {abs(pct_change):.1f}% "
            f"(from {previous:.0f} to {latest:.0f}), "
            f"exceeding {threshold}% threshold",
        )

    if direction == "increase" and pct_change >= threshold:
        return EvaluationResult(
            True,
            f"Inventory increased {pct_change:.1f}% "
            f"(from {previous:.0f} to {latest:.0f}), "
            f"exceeding {threshold}% threshold",
        )

    return EvaluationResult(
        False,
        f"Inventory change {pct_change:+.1f}% within threshold ({threshold}% {direction})",
    )


# ---------------------------------------------------------------------------
# Evaluator dispatch
# ---------------------------------------------------------------------------

_EVALUATORS = {
    "price_change": _evaluate_price_change,
    "lead_time": _evaluate_lead_time,
    "news_detect": _evaluate_news_detect,
    "inventory_change": _evaluate_inventory_change,
}


# ---------------------------------------------------------------------------
# Duplicate check
# ---------------------------------------------------------------------------

def _has_recent_alert(
    session: Session,
    rule_id: int,
    company_id: int,
) -> bool:
    """
    Check if an alert for this rule + company already exists
    within the DUPLICATE_WINDOW_HOURS window.

    Since Alert.description stores the rule_id tag, we match on
    company_id + a description containing the rule identifier.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DUPLICATE_WINDOW_HOURS)

    # We embed "[rule:{rule_id}]" in the alert description for dedup
    tag = f"[rule:{rule_id}]"

    statement = (
        select(Alert)
        .where(
            Alert.company_id == company_id,
            Alert.description.contains(tag),  # type: ignore[union-attr]
            Alert.created_at >= cutoff,
        )
        .limit(1)
    )
    return session.exec(statement).first() is not None


# ---------------------------------------------------------------------------
# Core: evaluate a single rule
# ---------------------------------------------------------------------------

def evaluate_rule(
    session: Session,
    rule: AlertRule,
) -> Alert | None:
    """
    Evaluate a single AlertRule and return an Alert if the condition is met,
    or None if not triggered / duplicate / error.
    """
    # --- Parse condition JSON ---
    try:
        condition: dict[str, Any] = json.loads(rule.condition)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning(
            "Malformed condition JSON for rule %s (id=%s): %s",
            rule.name,
            rule.id,
            exc,
        )
        return None

    rule_type = condition.get("rule_type")
    company_id = condition.get("company_id")

    if rule_type is None:
        logger.warning(
            "Rule %s (id=%s) missing 'rule_type' in condition",
            rule.name,
            rule.id,
        )
        return None

    if company_id is None:
        logger.warning(
            "Rule %s (id=%s) missing 'company_id' in condition",
            rule.name,
            rule.id,
        )
        return None

    evaluator = _EVALUATORS.get(rule_type)
    if evaluator is None:
        logger.warning(
            "Unknown rule_type '%s' for rule %s (id=%s)",
            rule_type,
            rule.name,
            rule.id,
        )
        return None

    # --- Evaluate ---
    result = evaluator(session, company_id, condition)

    if not result.triggered:
        logger.debug(
            "Rule '%s' (id=%s) not triggered: %s",
            rule.name,
            rule.id,
            result.message,
        )
        return None

    # --- Duplicate check ---
    if _has_recent_alert(session, rule.id, company_id):
        logger.debug(
            "Duplicate alert suppressed for rule '%s' (id=%s), company_id=%s",
            rule.name,
            rule.id,
            company_id,
        )
        return None

    # --- Create alert ---
    severity = SEVERITY_MAP.get(rule_type, "info")
    alert = Alert(
        company_id=company_id,
        severity=severity,
        title=f"[{rule_type}] {rule.name}",
        description=f"[rule:{rule.id}] {result.message}",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    session.add(alert)

    logger.info(
        "Alert created: rule='%s' (id=%s), company_id=%s, severity=%s - %s",
        rule.name,
        rule.id,
        company_id,
        severity,
        result.message,
    )

    return alert


# ---------------------------------------------------------------------------
# Main entry point: evaluate all active rules
# ---------------------------------------------------------------------------

def evaluate_all_rules(session: Session) -> list[Alert]:
    """
    Fetch all active AlertRules, evaluate each one, and return
    the list of newly created Alerts.

    This function does NOT commit -- the caller is responsible for
    committing the session.
    """
    statement = select(AlertRule).where(AlertRule.is_active == True)  # noqa: E712
    rules = session.exec(statement).all()

    logger.info("Evaluating %d active alert rules", len(rules))

    created_alerts: list[Alert] = []

    for rule in rules:
        try:
            alert = evaluate_rule(session, rule)
            if alert is not None:
                created_alerts.append(alert)
        except Exception:
            logger.exception(
                "Unexpected error evaluating rule '%s' (id=%s)",
                rule.name,
                rule.id,
            )

    logger.info(
        "Alert evaluation complete: %d rules evaluated, %d alerts created",
        len(rules),
        len(created_alerts),
    )

    return created_alerts


# ---------------------------------------------------------------------------
# Scheduler-compatible wrapper (creates its own session)
# ---------------------------------------------------------------------------

def run_alert_evaluation() -> None:
    """
    Standalone function for the scheduler.

    Creates its own Session, evaluates all rules, commits, and closes.
    Follows the same pattern as collect_stock_prices / collect_exchange_rates.
    """
    from app.core.database import engine

    with Session(engine) as session:
        try:
            evaluate_all_rules(session)
            session.commit()
        except Exception:
            logger.exception("Alert evaluation job failed")
            session.rollback()
