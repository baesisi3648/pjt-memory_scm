# @TASK T-ALERT-ENGINE - Alert evaluation engine tests
# @TEST tests/test_alert_engine.py

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session

from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.company import Company
from app.models.data_point import DataPoint
from app.models.data_source import DataSource
from app.models.news_item import NewsItem
from app.models.user import User
from app.core.security import hash_password
from app.services.alert_engine import (
    EvaluationResult,
    evaluate_all_rules,
    evaluate_rule,
    _evaluate_price_change,
    _evaluate_lead_time,
    _evaluate_news_detect,
    _evaluate_inventory_change,
    _has_recent_alert,
    DUPLICATE_WINDOW_HOURS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_user(session: Session) -> User:
    user = User(
        email="engine-test@example.com",
        hashed_password=hash_password("password123"),
        name="Engine Test User",
        role="analyst",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_company(session: Session, name: str = "TestCorp") -> Company:
    company = Company(name=name)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def _create_data_source(session: Session, name: str = "TestSource") -> DataSource:
    source = DataSource(name=name, type="api", is_active=True)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def _create_data_point(
    session: Session,
    source: DataSource,
    company: Company,
    metric: str,
    value: float,
    timestamp: datetime | None = None,
    unit: str | None = None,
) -> DataPoint:
    dp = DataPoint(
        source_id=source.id,
        company_id=company.id,
        metric=metric,
        value=value,
        unit=unit,
        timestamp=timestamp or _now(),
    )
    session.add(dp)
    session.commit()
    session.refresh(dp)
    return dp


def _create_rule(
    session: Session,
    user: User,
    name: str,
    condition: dict,
    is_active: bool = True,
) -> AlertRule:
    rule = AlertRule(
        user_id=user.id,
        name=name,
        condition=json.dumps(condition),
        is_active=is_active,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


def _create_news_item(
    session: Session,
    company: Company,
    sentiment: float,
    published_at: datetime | None = None,
    title: str = "Test News",
) -> NewsItem:
    item = NewsItem(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        source="TestSource",
        company_id=company.id,
        sentiment=sentiment,
        published_at=published_at or _now(),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Tests: _evaluate_price_change
# ---------------------------------------------------------------------------

class TestEvaluatePriceChange:
    """Tests for the price_change evaluator."""

    def test_price_drop_triggers(self, session: Session):
        """A price drop exceeding threshold triggers the rule."""
        company = _create_company(session)
        source = _create_data_source(session)

        # Older point first (higher price), then newer (lower price)
        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 90.0,
            timestamp=_now(),
        )

        result = _evaluate_price_change(
            session, company.id, {"threshold": 5, "direction": "drop"}
        )

        assert result.triggered is True
        assert "dropped" in result.message.lower()
        assert "10.0%" in result.message

    def test_price_drop_within_threshold(self, session: Session):
        """A small price drop within threshold does not trigger."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 97.0,
            timestamp=_now(),
        )

        result = _evaluate_price_change(
            session, company.id, {"threshold": 5, "direction": "drop"}
        )

        assert result.triggered is False

    def test_price_rise_triggers(self, session: Session):
        """A price rise exceeding threshold triggers when direction=rise."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 112.0,
            timestamp=_now(),
        )

        result = _evaluate_price_change(
            session, company.id, {"threshold": 10, "direction": "rise"}
        )

        assert result.triggered is True
        assert "rose" in result.message.lower()

    def test_insufficient_data_points(self, session: Session):
        """Only one data point returns not-triggered."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "stock_price", 100.0,
        )

        result = _evaluate_price_change(
            session, company.id, {"threshold": 5, "direction": "drop"}
        )

        assert result.triggered is False
        assert "insufficient" in result.message.lower()

    def test_no_data_points(self, session: Session):
        """No data points at all returns not-triggered."""
        company = _create_company(session)

        result = _evaluate_price_change(
            session, company.id, {"threshold": 5, "direction": "drop"}
        )

        assert result.triggered is False
        assert "insufficient" in result.message.lower()

    def test_missing_threshold(self, session: Session):
        """Missing threshold in condition returns not-triggered."""
        company = _create_company(session)

        result = _evaluate_price_change(
            session, company.id, {"direction": "drop"}
        )

        assert result.triggered is False
        assert "missing" in result.message.lower()

    def test_previous_price_zero(self, session: Session):
        """Previous price of zero returns not-triggered (avoid division by zero)."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "stock_price", 0.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 50.0,
            timestamp=_now(),
        )

        result = _evaluate_price_change(
            session, company.id, {"threshold": 5, "direction": "drop"}
        )

        assert result.triggered is False
        assert "zero" in result.message.lower()

    def test_old_data_points_excluded(self, session: Session):
        """Data points older than RECENT_DATA_HOURS are excluded."""
        company = _create_company(session)
        source = _create_data_source(session)

        # Both data points are very old (beyond the 48h window)
        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=100),
        )
        _create_data_point(
            session, source, company, "stock_price", 50.0,
            timestamp=_now() - timedelta(hours=99),
        )

        result = _evaluate_price_change(
            session, company.id, {"threshold": 5, "direction": "drop"}
        )

        assert result.triggered is False
        assert "insufficient" in result.message.lower()


# ---------------------------------------------------------------------------
# Tests: _evaluate_lead_time
# ---------------------------------------------------------------------------

class TestEvaluateLeadTime:
    """Tests for the lead_time evaluator."""

    def test_lead_time_exceeds_threshold(self, session: Session):
        """Lead time above threshold triggers."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "lead_time", 45.0,
        )

        result = _evaluate_lead_time(
            session, company.id, {"threshold": 30, "unit": "days"}
        )

        assert result.triggered is True
        assert "45" in result.message
        assert "exceeds" in result.message.lower()

    def test_lead_time_within_threshold(self, session: Session):
        """Lead time within threshold does not trigger."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "lead_time", 20.0,
        )

        result = _evaluate_lead_time(
            session, company.id, {"threshold": 30, "unit": "days"}
        )

        assert result.triggered is False

    def test_no_lead_time_data(self, session: Session):
        """No lead_time data available returns not-triggered."""
        company = _create_company(session)

        result = _evaluate_lead_time(
            session, company.id, {"threshold": 30, "unit": "days"}
        )

        assert result.triggered is False
        assert "no recent" in result.message.lower()

    def test_missing_threshold(self, session: Session):
        """Missing threshold in condition returns not-triggered."""
        company = _create_company(session)

        result = _evaluate_lead_time(
            session, company.id, {"unit": "days"}
        )

        assert result.triggered is False
        assert "missing" in result.message.lower()


# ---------------------------------------------------------------------------
# Tests: _evaluate_news_detect
# ---------------------------------------------------------------------------

class TestEvaluateNewsDetect:
    """Tests for the news_detect evaluator."""

    def test_enough_negative_articles_triggers(self, session: Session):
        """Meeting min_articles with bad sentiment triggers."""
        company = _create_company(session)

        for i in range(4):
            _create_news_item(session, company, sentiment=-0.5, title=f"Bad News {i}")

        result = _evaluate_news_detect(
            session, company.id, {"min_articles": 3, "sentiment_below": -0.3}
        )

        assert result.triggered is True
        assert "4" in result.message

    def test_not_enough_negative_articles(self, session: Session):
        """Fewer than min_articles does not trigger."""
        company = _create_company(session)

        _create_news_item(session, company, sentiment=-0.5, title="Bad News 1")
        _create_news_item(session, company, sentiment=-0.4, title="Bad News 2")

        result = _evaluate_news_detect(
            session, company.id, {"min_articles": 3, "sentiment_below": -0.3}
        )

        assert result.triggered is False

    def test_positive_sentiment_not_counted(self, session: Session):
        """Articles with sentiment above threshold are not counted."""
        company = _create_company(session)

        # 2 negative, 3 positive -- only 2 meet the criteria
        _create_news_item(session, company, sentiment=-0.5, title="Bad 1")
        _create_news_item(session, company, sentiment=-0.4, title="Bad 2")
        _create_news_item(session, company, sentiment=0.1, title="Good 1")
        _create_news_item(session, company, sentiment=0.5, title="Good 2")
        _create_news_item(session, company, sentiment=0.8, title="Good 3")

        result = _evaluate_news_detect(
            session, company.id, {"min_articles": 3, "sentiment_below": -0.3}
        )

        assert result.triggered is False

    def test_no_news_items(self, session: Session):
        """No news items returns not-triggered."""
        company = _create_company(session)

        result = _evaluate_news_detect(
            session, company.id, {"min_articles": 3, "sentiment_below": -0.3}
        )

        assert result.triggered is False

    def test_old_articles_excluded(self, session: Session):
        """Articles older than RECENT_NEWS_HOURS are excluded."""
        company = _create_company(session)

        for i in range(5):
            _create_news_item(
                session, company, sentiment=-0.8,
                title=f"Old Bad {i}",
                published_at=_now() - timedelta(hours=48),
            )

        result = _evaluate_news_detect(
            session, company.id, {"min_articles": 3, "sentiment_below": -0.3}
        )

        assert result.triggered is False


# ---------------------------------------------------------------------------
# Tests: _evaluate_inventory_change
# ---------------------------------------------------------------------------

class TestEvaluateInventoryChange:
    """Tests for the inventory_change evaluator."""

    def test_inventory_decrease_triggers(self, session: Session):
        """Inventory decrease exceeding threshold triggers."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "inventory", 1000.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "inventory", 700.0,
            timestamp=_now(),
        )

        result = _evaluate_inventory_change(
            session, company.id, {"threshold": 20, "direction": "decrease"}
        )

        assert result.triggered is True
        assert "decreased" in result.message.lower()

    def test_inventory_increase_triggers(self, session: Session):
        """Inventory increase exceeding threshold triggers when direction=increase."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "inventory", 1000.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "inventory", 1300.0,
            timestamp=_now(),
        )

        result = _evaluate_inventory_change(
            session, company.id, {"threshold": 20, "direction": "increase"}
        )

        assert result.triggered is True
        assert "increased" in result.message.lower()

    def test_inventory_within_threshold(self, session: Session):
        """Small inventory change within threshold does not trigger."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "inventory", 1000.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "inventory", 950.0,
            timestamp=_now(),
        )

        result = _evaluate_inventory_change(
            session, company.id, {"threshold": 20, "direction": "decrease"}
        )

        assert result.triggered is False

    def test_insufficient_inventory_data(self, session: Session):
        """Only one inventory data point returns not-triggered."""
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "inventory", 1000.0,
        )

        result = _evaluate_inventory_change(
            session, company.id, {"threshold": 20, "direction": "decrease"}
        )

        assert result.triggered is False
        assert "insufficient" in result.message.lower()

    def test_missing_threshold(self, session: Session):
        """Missing threshold in condition returns not-triggered."""
        company = _create_company(session)

        result = _evaluate_inventory_change(
            session, company.id, {"direction": "decrease"}
        )

        assert result.triggered is False
        assert "missing" in result.message.lower()


# ---------------------------------------------------------------------------
# Tests: _has_recent_alert (duplicate check)
# ---------------------------------------------------------------------------

class TestHasRecentAlert:
    """Tests for duplicate alert detection."""

    def test_no_existing_alert(self, session: Session):
        """No existing alerts means no duplicate."""
        company = _create_company(session)

        assert _has_recent_alert(session, rule_id=1, company_id=company.id) is False

    def test_recent_alert_is_duplicate(self, session: Session):
        """Alert within the duplicate window is detected."""
        company = _create_company(session)

        alert = Alert(
            company_id=company.id,
            severity="warning",
            title="[price_change] Test Rule",
            description="[rule:42] Price dropped 10%",
            is_read=False,
            created_at=_now() - timedelta(hours=1),
        )
        session.add(alert)
        session.commit()

        assert _has_recent_alert(session, rule_id=42, company_id=company.id) is True

    def test_old_alert_not_duplicate(self, session: Session):
        """Alert older than the duplicate window is not a duplicate."""
        company = _create_company(session)

        alert = Alert(
            company_id=company.id,
            severity="warning",
            title="[price_change] Test Rule",
            description="[rule:42] Price dropped 10%",
            is_read=False,
            created_at=_now() - timedelta(hours=DUPLICATE_WINDOW_HOURS + 1),
        )
        session.add(alert)
        session.commit()

        assert _has_recent_alert(session, rule_id=42, company_id=company.id) is False

    def test_different_rule_not_duplicate(self, session: Session):
        """Alert for a different rule_id is not a duplicate."""
        company = _create_company(session)

        alert = Alert(
            company_id=company.id,
            severity="warning",
            title="[price_change] Other Rule",
            description="[rule:99] Some other alert",
            is_read=False,
            created_at=_now(),
        )
        session.add(alert)
        session.commit()

        assert _has_recent_alert(session, rule_id=42, company_id=company.id) is False

    def test_different_company_not_duplicate(self, session: Session):
        """Alert for a different company_id is not a duplicate."""
        company_a = _create_company(session, name="CompanyA")
        company_b = _create_company(session, name="CompanyB")

        alert = Alert(
            company_id=company_a.id,
            severity="warning",
            title="[price_change] Test Rule",
            description="[rule:42] Price dropped 10%",
            is_read=False,
            created_at=_now(),
        )
        session.add(alert)
        session.commit()

        assert _has_recent_alert(session, rule_id=42, company_id=company_b.id) is False


# ---------------------------------------------------------------------------
# Tests: evaluate_rule (integration of parsing + evaluation + dedup)
# ---------------------------------------------------------------------------

class TestEvaluateRule:
    """Tests for the evaluate_rule orchestrator function."""

    def test_triggers_and_creates_alert(self, session: Session):
        """A rule whose condition is met produces an Alert object."""
        user = _create_user(session)
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 80.0,
            timestamp=_now(),
        )

        rule = _create_rule(session, user, "Big Drop Alert", {
            "rule_type": "price_change",
            "company_id": company.id,
            "threshold": 5,
            "direction": "drop",
        })

        alert = evaluate_rule(session, rule)

        assert alert is not None
        assert alert.company_id == company.id
        assert alert.severity == "warning"
        assert "[price_change]" in alert.title
        assert f"[rule:{rule.id}]" in alert.description

    def test_not_triggered_returns_none(self, session: Session):
        """A rule whose condition is not met returns None."""
        user = _create_user(session)
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 99.0,
            timestamp=_now(),
        )

        rule = _create_rule(session, user, "Minor Change", {
            "rule_type": "price_change",
            "company_id": company.id,
            "threshold": 5,
            "direction": "drop",
        })

        alert = evaluate_rule(session, rule)

        assert alert is None

    def test_malformed_json_returns_none(self, session: Session):
        """Malformed condition JSON returns None and does not raise."""
        user = _create_user(session)
        rule = AlertRule(
            user_id=user.id,
            name="Bad JSON Rule",
            condition="not valid json {{{",
            is_active=True,
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)

        alert = evaluate_rule(session, rule)

        assert alert is None

    def test_missing_rule_type_returns_none(self, session: Session):
        """Condition without rule_type returns None."""
        user = _create_user(session)
        rule = _create_rule(session, user, "No Type", {
            "company_id": 1,
            "threshold": 5,
        })

        alert = evaluate_rule(session, rule)

        assert alert is None

    def test_missing_company_id_returns_none(self, session: Session):
        """Condition without company_id returns None."""
        user = _create_user(session)
        rule = _create_rule(session, user, "No Company", {
            "rule_type": "price_change",
            "threshold": 5,
            "direction": "drop",
        })

        alert = evaluate_rule(session, rule)

        assert alert is None

    def test_unknown_rule_type_returns_none(self, session: Session):
        """Unknown rule_type returns None."""
        user = _create_user(session)
        rule = _create_rule(session, user, "Unknown Type", {
            "rule_type": "alien_invasion",
            "company_id": 1,
        })

        alert = evaluate_rule(session, rule)

        assert alert is None

    def test_duplicate_alert_suppressed(self, session: Session):
        """A second evaluation within 24h does not create a duplicate alert."""
        user = _create_user(session)
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 80.0,
            timestamp=_now(),
        )

        rule = _create_rule(session, user, "Drop Alert", {
            "rule_type": "price_change",
            "company_id": company.id,
            "threshold": 5,
            "direction": "drop",
        })

        # First evaluation creates an alert
        alert1 = evaluate_rule(session, rule)
        session.commit()
        assert alert1 is not None

        # Second evaluation should be suppressed
        alert2 = evaluate_rule(session, rule)
        assert alert2 is None

    def test_lead_time_rule_severity_is_critical(self, session: Session):
        """lead_time rules produce 'critical' severity alerts."""
        user = _create_user(session)
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "lead_time", 50.0,
        )

        rule = _create_rule(session, user, "Lead Time Alert", {
            "rule_type": "lead_time",
            "company_id": company.id,
            "threshold": 30,
            "unit": "days",
        })

        alert = evaluate_rule(session, rule)

        assert alert is not None
        assert alert.severity == "critical"

    def test_news_detect_rule(self, session: Session):
        """news_detect rule triggers with enough negative articles."""
        user = _create_user(session)
        company = _create_company(session)

        for i in range(5):
            _create_news_item(session, company, sentiment=-0.7, title=f"Disaster {i}")

        rule = _create_rule(session, user, "Bad Press Alert", {
            "rule_type": "news_detect",
            "company_id": company.id,
            "min_articles": 3,
            "sentiment_below": -0.3,
        })

        alert = evaluate_rule(session, rule)

        assert alert is not None
        assert alert.severity == "warning"
        assert "[news_detect]" in alert.title


# ---------------------------------------------------------------------------
# Tests: evaluate_all_rules (full pipeline)
# ---------------------------------------------------------------------------

class TestEvaluateAllRules:
    """Tests for the evaluate_all_rules main entry point."""

    def test_evaluates_only_active_rules(self, session: Session):
        """Only active rules are evaluated."""
        user = _create_user(session)
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "lead_time", 50.0,
        )

        active_rule = _create_rule(session, user, "Active Rule", {
            "rule_type": "lead_time",
            "company_id": company.id,
            "threshold": 30,
            "unit": "days",
        }, is_active=True)

        inactive_rule = _create_rule(session, user, "Inactive Rule", {
            "rule_type": "lead_time",
            "company_id": company.id,
            "threshold": 30,
            "unit": "days",
        }, is_active=False)

        alerts = evaluate_all_rules(session)

        assert len(alerts) == 1
        assert alerts[0].title == f"[lead_time] Active Rule"

    def test_multiple_rules_multiple_alerts(self, session: Session):
        """Multiple triggered rules create multiple alerts."""
        user = _create_user(session)
        company = _create_company(session)
        source = _create_data_source(session)

        # Price data
        _create_data_point(
            session, source, company, "stock_price", 100.0,
            timestamp=_now() - timedelta(hours=1),
        )
        _create_data_point(
            session, source, company, "stock_price", 80.0,
            timestamp=_now(),
        )

        # Lead time data
        _create_data_point(
            session, source, company, "lead_time", 50.0,
        )

        _create_rule(session, user, "Price Drop", {
            "rule_type": "price_change",
            "company_id": company.id,
            "threshold": 5,
            "direction": "drop",
        })
        _create_rule(session, user, "Lead Time High", {
            "rule_type": "lead_time",
            "company_id": company.id,
            "threshold": 30,
            "unit": "days",
        })

        alerts = evaluate_all_rules(session)

        assert len(alerts) == 2

    def test_empty_rules_returns_empty(self, session: Session):
        """No active rules returns an empty list without errors."""
        alerts = evaluate_all_rules(session)

        assert alerts == []

    def test_bad_rule_does_not_break_others(self, session: Session):
        """A malformed rule does not prevent other rules from being evaluated."""
        user = _create_user(session)
        company = _create_company(session)
        source = _create_data_source(session)

        _create_data_point(
            session, source, company, "lead_time", 50.0,
        )

        # Bad rule (malformed JSON)
        bad_rule = AlertRule(
            user_id=user.id,
            name="Bad Rule",
            condition="broken json",
            is_active=True,
        )
        session.add(bad_rule)
        session.commit()

        # Good rule
        _create_rule(session, user, "Good Rule", {
            "rule_type": "lead_time",
            "company_id": company.id,
            "threshold": 30,
            "unit": "days",
        })

        alerts = evaluate_all_rules(session)

        # The good rule should still produce an alert
        assert len(alerts) == 1
        assert alerts[0].title == "[lead_time] Good Rule"

    def test_no_data_for_company_skips_gracefully(self, session: Session):
        """Rules for a company with no data are skipped without error."""
        user = _create_user(session)
        company = _create_company(session)

        _create_rule(session, user, "No Data Rule", {
            "rule_type": "price_change",
            "company_id": company.id,
            "threshold": 5,
            "direction": "drop",
        })

        alerts = evaluate_all_rules(session)

        assert alerts == []
