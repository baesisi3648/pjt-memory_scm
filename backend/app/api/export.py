# @TASK EXPORT-1 - Report export API endpoints (CSV and PDF)
# @SPEC docs/planning/02-trd.md#export-api
# @TEST tests/test_export.py

import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.user import User
from app.services.export_service import (
    export_alerts_csv,
    export_companies_csv,
    export_relations_csv,
    export_supply_chain_report_pdf,
)

router = APIRouter()

_DATE_FMT = "%Y%m%d"


def _csv_response(content: str, filename: str) -> StreamingResponse:
    """Create a StreamingResponse for CSV file download."""
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _pdf_response(content: bytes, filename: str) -> StreamingResponse:
    """Create a StreamingResponse for PDF file download."""
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# @TASK EXPORT-1.1 - Companies CSV export endpoint
@router.get("/companies.csv")
def download_companies_csv(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Download all companies as a CSV file.

    Layer 1: Authentication required (get_current_user)
    Layer 4: Structured CSV output with BOM for Excel compatibility
    """
    csv_content = export_companies_csv(session)
    datestamp = datetime.now(timezone.utc).strftime(_DATE_FMT)
    return _csv_response(csv_content, f"companies_{datestamp}.csv")


# @TASK EXPORT-1.2 - Alerts CSV export endpoint
@router.get("/alerts.csv")
def download_alerts_csv(
    company_id: Optional[int] = Query(
        default=None,
        description="Filter alerts by company ID",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Download alerts as a CSV file, optionally filtered by company.

    Layer 1: Authentication required (get_current_user)
    Layer 2: Optional domain filter (company_id)
    Layer 4: Structured CSV output with BOM for Excel compatibility
    """
    csv_content = export_alerts_csv(session, company_id=company_id)
    datestamp = datetime.now(timezone.utc).strftime(_DATE_FMT)
    suffix = f"_company{company_id}" if company_id is not None else ""
    return _csv_response(csv_content, f"alerts{suffix}_{datestamp}.csv")


# @TASK EXPORT-1.3 - Relations CSV export endpoint
@router.get("/relations.csv")
def download_relations_csv(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Download supply chain relations as a CSV file.

    Layer 1: Authentication required (get_current_user)
    Layer 4: Structured CSV output with BOM for Excel compatibility
    """
    csv_content = export_relations_csv(session)
    datestamp = datetime.now(timezone.utc).strftime(_DATE_FMT)
    return _csv_response(csv_content, f"relations_{datestamp}.csv")


# @TASK EXPORT-1.4 - Full PDF report endpoint
@router.get("/report.pdf")
def download_report_pdf(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Download a full supply chain intelligence report as PDF.

    Layer 1: Authentication required (get_current_user)
    Layer 4: Structured PDF output with tables and summary
    """
    pdf_bytes = export_supply_chain_report_pdf(session)
    datestamp = datetime.now(timezone.utc).strftime(_DATE_FMT)
    return _pdf_response(pdf_bytes, f"supply_chain_report_{datestamp}.pdf")
