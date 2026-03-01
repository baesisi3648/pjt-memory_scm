# @TASK EXPORT-1 - Report export service (CSV and PDF)
# @SPEC docs/planning/02-trd.md#export-api

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlmodel import Session, func, select

from app.models.alert import Alert
from app.models.company import Company
from app.models.company_relation import CompanyRelation


# ---------------------------------------------------------------------------
# CSV Exports
# ---------------------------------------------------------------------------

BOM = "\ufeff"  # UTF-8 BOM for Excel compatibility


def export_companies_csv(session: Session) -> str:
    """Export all companies as CSV with tier, cluster, and country columns.

    Returns a UTF-8 string (BOM-prefixed) suitable for streaming as a file
    download.
    """
    companies = session.exec(
        select(Company).order_by(Company.id)
    ).all()

    buf = io.StringIO()
    buf.write(BOM)
    writer = csv.writer(buf)
    writer.writerow(["id", "name", "name_kr", "tier", "country", "ticker", "cluster_id", "created_at"])

    for c in companies:
        writer.writerow([
            c.id,
            c.name,
            c.name_kr or "",
            c.tier or "",
            c.country or "",
            c.ticker or "",
            c.cluster_id or "",
            c.created_at.isoformat() if c.created_at else "",
        ])

    return buf.getvalue()


def export_alerts_csv(
    session: Session,
    company_id: Optional[int] = None,
) -> str:
    """Export alerts as CSV, optionally filtered by company_id.

    Returns a UTF-8 string (BOM-prefixed) suitable for streaming as a file
    download.
    """
    stmt = select(Alert).order_by(Alert.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(Alert.company_id == company_id)

    alerts = session.exec(stmt).all()

    buf = io.StringIO()
    buf.write(BOM)
    writer = csv.writer(buf)
    writer.writerow(["id", "company_id", "severity", "title", "description", "is_read", "created_at"])

    for a in alerts:
        writer.writerow([
            a.id,
            a.company_id or "",
            a.severity,
            a.title,
            a.description or "",
            a.is_read,
            a.created_at.isoformat() if a.created_at else "",
        ])

    return buf.getvalue()


def export_relations_csv(session: Session) -> str:
    """Export all supply chain relations as CSV.

    Returns a UTF-8 string (BOM-prefixed) suitable for streaming as a file
    download.
    """
    relations = session.exec(
        select(CompanyRelation).order_by(CompanyRelation.id)
    ).all()

    # Build a quick id->name lookup to enrich the output.
    company_ids = set()
    for r in relations:
        company_ids.add(r.source_id)
        company_ids.add(r.target_id)

    name_map: dict[int, str] = {}
    if company_ids:
        companies = session.exec(
            select(Company).where(Company.id.in_(list(company_ids)))
        ).all()
        name_map = {c.id: c.name for c in companies}

    buf = io.StringIO()
    buf.write(BOM)
    writer = csv.writer(buf)
    writer.writerow([
        "id", "source_id", "source_name", "target_id", "target_name",
        "relation_type", "strength",
    ])

    for r in relations:
        writer.writerow([
            r.id,
            r.source_id,
            name_map.get(r.source_id, ""),
            r.target_id,
            name_map.get(r.target_id, ""),
            r.relation_type,
            r.strength if r.strength is not None else "",
        ])

    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

def export_supply_chain_report_pdf(session: Session) -> bytes:
    """Generate a full supply chain intelligence report as PDF bytes.

    The report contains:
    - Title and generation date
    - Summary section (total companies, alert counts by severity)
    - Companies table (name, tier, country, alert count)
    - Recent alerts table (date, company, severity, title)
    """
    # -- Gather data -------------------------------------------------------
    companies = session.exec(select(Company).order_by(Company.name)).all()
    alerts = session.exec(
        select(Alert).order_by(Alert.created_at.desc())
    ).all()

    company_name_map: dict[int, str] = {c.id: c.name for c in companies}

    # Alert counts by severity
    severity_counts: dict[str, int] = {}
    alert_count_by_company: dict[int, int] = {}
    for a in alerts:
        severity_counts[a.severity] = severity_counts.get(a.severity, 0) + 1
        if a.company_id is not None:
            alert_count_by_company[a.company_id] = (
                alert_count_by_company.get(a.company_id, 0) + 1
            )

    # -- Build PDF ---------------------------------------------------------
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=6 * mm,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=8 * mm,
        spaceAfter=4 * mm,
    )
    body_style = styles["BodyText"]

    elements: list = []

    # Title
    elements.append(Paragraph("Supply Chain Intelligence Report", title_style))
    elements.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            body_style,
        )
    )
    elements.append(Spacer(1, 6 * mm))

    # -- Summary section ---------------------------------------------------
    elements.append(Paragraph("Summary", heading_style))

    summary_lines = [
        f"Total companies: {len(companies)}",
        f"Total alerts: {len(alerts)}",
    ]
    for sev in ("critical", "warning", "info"):
        count = severity_counts.get(sev, 0)
        summary_lines.append(f"  - {sev.capitalize()}: {count}")

    # Risk highlights: companies with the most critical alerts
    critical_companies = sorted(
        [
            (cid, cnt)
            for cid, cnt in alert_count_by_company.items()
        ],
        key=lambda x: x[1],
        reverse=True,
    )[:5]
    if critical_companies:
        summary_lines.append("")
        summary_lines.append("Top risk companies (by alert count):")
        for cid, cnt in critical_companies:
            cname = company_name_map.get(cid, f"ID {cid}")
            summary_lines.append(f"  - {cname}: {cnt} alert(s)")

    for line in summary_lines:
        elements.append(Paragraph(line, body_style))

    elements.append(Spacer(1, 4 * mm))

    # -- Companies table ---------------------------------------------------
    elements.append(Paragraph("Companies", heading_style))

    company_table_data = [["Name", "Tier", "Country", "Alerts"]]
    for c in companies:
        company_table_data.append([
            c.name,
            c.tier or "-",
            c.country or "-",
            str(alert_count_by_company.get(c.id, 0)),
        ])

    if len(company_table_data) > 1:
        col_widths = [60 * mm, 30 * mm, 40 * mm, 20 * mm]
        company_table = Table(company_table_data, colWidths=col_widths, repeatRows=1)
        company_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(company_table)
    else:
        elements.append(Paragraph("No companies found.", body_style))

    elements.append(Spacer(1, 4 * mm))

    # -- Recent alerts table -----------------------------------------------
    elements.append(Paragraph("Recent Alerts", heading_style))

    recent_alerts = alerts[:50]  # cap at 50 most recent
    alert_table_data = [["Date", "Company", "Severity", "Title"]]
    for a in recent_alerts:
        cname = company_name_map.get(a.company_id, "-") if a.company_id else "-"
        date_str = a.created_at.strftime("%Y-%m-%d") if a.created_at else "-"
        # Truncate long titles to prevent table overflow
        title_text = a.title if len(a.title) <= 60 else a.title[:57] + "..."
        alert_table_data.append([date_str, cname, a.severity, title_text])

    if len(alert_table_data) > 1:
        alert_col_widths = [25 * mm, 40 * mm, 20 * mm, 65 * mm]
        alert_table = Table(alert_table_data, colWidths=alert_col_widths, repeatRows=1)
        alert_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(alert_table)
    else:
        elements.append(Paragraph("No alerts found.", body_style))

    # -- Build and return --------------------------------------------------
    doc.build(elements)
    return buf.getvalue()
