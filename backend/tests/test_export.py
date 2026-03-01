# @TASK EXPORT-1 - Export endpoint tests
# @TEST tests/test_export.py

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.alert import Alert
from app.models.cluster import Cluster
from app.models.company import Company
from app.models.company_relation import CompanyRelation
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(session: Session) -> User:
    """Insert a test user and return it."""
    user = User(
        email="export-test@example.com",
        hashed_password=hash_password("password123"),
        name="Export Test User",
        role="analyst",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _auth_header(user: User) -> dict:
    """Build an Authorization header for the given user."""
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _seed_data(session: Session) -> dict:
    """Create sample companies, alerts, and relations for testing."""
    cluster = Cluster(name="FAB", tier="fab")
    session.add(cluster)
    session.commit()
    session.refresh(cluster)

    companies = [
        Company(name="Samsung", tier="tier1", cluster_id=cluster.id, country="KR"),
        Company(name="SK Hynix", tier="tier1", cluster_id=cluster.id, country="KR"),
    ]
    session.add_all(companies)
    session.commit()
    for c in companies:
        session.refresh(c)

    alerts = [
        Alert(
            company_id=companies[0].id,
            severity="critical",
            title="Supply shortage detected",
        ),
        Alert(
            company_id=companies[0].id,
            severity="warning",
            title="Price volatility increase",
        ),
        Alert(
            company_id=companies[1].id,
            severity="info",
            title="New partnership announced",
        ),
    ]
    session.add_all(alerts)
    session.commit()

    relation = CompanyRelation(
        source_id=companies[0].id,
        target_id=companies[1].id,
        relation_type="supplier",
        strength=0.8,
    )
    session.add(relation)
    session.commit()

    return {
        "companies": companies,
        "alerts": alerts,
        "relation": relation,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/export/companies.csv
# ---------------------------------------------------------------------------

def test_export_companies_csv(session: Session, client: TestClient):
    """Companies CSV download returns valid CSV with correct headers."""
    user = _create_test_user(session)
    _seed_data(session)

    response = client.get(
        "/api/v1/export/companies.csv",
        headers=_auth_header(user),
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "companies_" in response.headers["content-disposition"]

    text = response.text
    # BOM check
    assert text.startswith("\ufeff")
    # Header row
    assert "id,name,name_kr,tier,country,ticker,cluster_id,created_at" in text
    # Data rows
    assert "Samsung" in text
    assert "SK Hynix" in text


def test_export_companies_csv_empty(session: Session, client: TestClient):
    """Companies CSV works with no data (header only)."""
    user = _create_test_user(session)

    response = client.get(
        "/api/v1/export/companies.csv",
        headers=_auth_header(user),
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    # BOM + header row only
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# GET /api/v1/export/alerts.csv
# ---------------------------------------------------------------------------

def test_export_alerts_csv(session: Session, client: TestClient):
    """Alerts CSV download returns all alerts."""
    user = _create_test_user(session)
    _seed_data(session)

    response = client.get(
        "/api/v1/export/alerts.csv",
        headers=_auth_header(user),
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    text = response.text
    assert text.startswith("\ufeff")
    assert "id,company_id,severity,title,description,is_read,created_at" in text
    assert "Supply shortage detected" in text
    assert "Price volatility increase" in text
    assert "New partnership announced" in text


def test_export_alerts_csv_filtered_by_company(session: Session, client: TestClient):
    """Alerts CSV filtered by company_id returns only matching alerts."""
    user = _create_test_user(session)
    data = _seed_data(session)
    company_id = data["companies"][0].id

    response = client.get(
        f"/api/v1/export/alerts.csv?company_id={company_id}",
        headers=_auth_header(user),
    )

    assert response.status_code == 200
    text = response.text
    assert "Supply shortage detected" in text
    assert "Price volatility increase" in text
    # SK Hynix alert should not appear
    assert "New partnership announced" not in text
    # Filename includes company suffix
    assert f"company{company_id}" in response.headers["content-disposition"]


# ---------------------------------------------------------------------------
# GET /api/v1/export/relations.csv
# ---------------------------------------------------------------------------

def test_export_relations_csv(session: Session, client: TestClient):
    """Relations CSV includes source/target names."""
    user = _create_test_user(session)
    _seed_data(session)

    response = client.get(
        "/api/v1/export/relations.csv",
        headers=_auth_header(user),
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    text = response.text
    assert text.startswith("\ufeff")
    assert "source_id,source_name,target_id,target_name" in text
    assert "Samsung" in text
    assert "SK Hynix" in text
    assert "supplier" in text


# ---------------------------------------------------------------------------
# GET /api/v1/export/report.pdf
# ---------------------------------------------------------------------------

def test_export_report_pdf(session: Session, client: TestClient):
    """PDF report downloads successfully with correct content-type."""
    user = _create_test_user(session)
    _seed_data(session)

    response = client.get(
        "/api/v1/export/report.pdf",
        headers=_auth_header(user),
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "supply_chain_report_" in response.headers["content-disposition"]
    # PDF magic bytes
    assert response.content[:5] == b"%PDF-"


def test_export_report_pdf_empty(session: Session, client: TestClient):
    """PDF report works even with no data."""
    user = _create_test_user(session)

    response = client.get(
        "/api/v1/export/report.pdf",
        headers=_auth_header(user),
    )

    assert response.status_code == 200
    assert response.content[:5] == b"%PDF-"
