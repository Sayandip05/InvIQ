"""
Admin Dashboard API — Super Admin endpoints for platform management.

Provides overview stats, user management summaries, and audit trail
access for the platform owner's dashboard.
"""

import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, require_admin
from app.infrastructure.database.models import User, AuditLog
from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.database.audit_repo import AuditRepository
from app.application.report_service import ReportService

logger = logging.getLogger("smart_inventory.admin")

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


# ── GET /admin/overview ────────────────────────────────────────────────────


@router.get("/overview", response_model=dict)
def get_platform_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Super Admin overview — quick stats for the entire platform.
    Shows total users, active/inactive counts, role breakdown, recent activity.
    """
    user_repo = UserRepository(db)

    total_users = user_repo.count()
    active_users = user_repo.count_filtered(is_active=True)
    inactive_users = user_repo.count_filtered(is_active=False)

    # Role breakdown
    role_counts = {}
    for role in ["admin", "manager", "staff", "vendor"]:
        role_counts[role] = user_repo.count_filtered(role=role)

    # Recent signups (last 7 days)
    recent_users = user_repo.get_all_filtered(limit=5)
    recent_signups = [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in recent_users
    ]

    # Recent audit events
    audit_repo = AuditRepository(db)
    recent_events = audit_repo.get_recent(limit=10)
    recent_activity = [
        {
            "action": e.action,
            "username": e.username,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "created_at": str(e.created_at) if e.created_at else None,
            "ip_address": e.ip_address,
        }
        for e in recent_events
    ]

    return {
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users,
                "by_role": role_counts,
            },
            "recent_signups": recent_signups,
            "recent_activity": recent_activity,
        },
    }


# ── GET /admin/audit-logs ─────────────────────────────────────────────────


@router.get("/audit-logs", response_model=dict)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    username: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    View audit trail — filterable by user, action type, or resource.
    This is the core compliance tool for the super admin.
    """
    audit_repo = AuditRepository(db)

    if username:
        logs = audit_repo.get_by_user(username, limit=limit)
    else:
        logs = audit_repo.get_recent(limit=limit)

    # Apply additional filters in-memory (small dataset)
    if action:
        logs = [l for l in logs if l.action == action]
    if resource_type:
        logs = [l for l in logs if l.resource_type == resource_type]

    return {
        "success": True,
        "data": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": str(log.created_at) if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }


# ── GET /admin/users/summary ──────────────────────────────────────────────


@router.get("/users/summary", response_model=dict)
def get_users_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Detailed user summary for the super admin user management section.
    """
    user_repo = UserRepository(db)
    all_users = user_repo.get_all()

    users_data = []
    for u in all_users:
        users_data.append(
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "login_attempts": u.login_attempts or 0,
                "locked_until": str(u.locked_until) if u.locked_until else None,
                "last_login_at": str(u.last_login_at) if u.last_login_at else None,
                "created_at": str(u.created_at) if u.created_at else None,
                "updated_at": str(u.updated_at) if u.updated_at else None,
            }
        )

    # Identify concerns
    locked_users = [u for u in users_data if u["locked_until"] is not None]
    never_logged_in = [
        u for u in users_data if u["last_login_at"] is None and u["role"] != "admin"
    ]

    return {
        "success": True,
        "data": {
            "all_users": users_data,
            "total": len(users_data),
            "alerts": {
                "locked_accounts": locked_users,
                "never_logged_in": never_logged_in,
            },
        },
    }


# ── GET /admin/reports/generate ────────────────────────────────────────────


@router.get("/reports/generate")
def generate_pdf_report(
    report_type: str = Query("inventory", description="inventory | transactions | requisitions | low_stock"),
    location_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Generate and stream a PDF report.
    Supports: inventory, transactions, requisitions, low_stock

    Data fetching is delegated to ReportService (application layer).
    This handler only constructs the PDF from the returned plain dicts.
    """
    from io import BytesIO
    from fastapi.responses import StreamingResponse

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab is not installed on the server")

    # ── Data layer — all queries go through the service ──────────────────
    svc = ReportService(db)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    report_titles = {
        "inventory":    "Inventory Stock Report",
        "transactions": "Transaction History Report",
        "requisitions": "Requisitions Report",
        "low_stock":    "Low Stock Alert Report",
    }
    title = report_titles.get(report_type, "Inventory Report")

    elements.append(Paragraph(f"InvIQ — {title}", styles["Title"]))
    elements.append(Paragraph(
        f"Generated by: {current_user.username}  |  "
        f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Normal"],
    ))
    if date_from or date_to:
        elements.append(Paragraph(
            f"Period: {date_from or 'beginning'} to {date_to or 'today'}",
            styles["Normal"],
        ))
    elements.append(Spacer(1, 0.3 * inch))

    # ── Shared header table style ─────────────────────────────────────────
    HEADER_STYLE = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]

    # ── INVENTORY / LOW_STOCK REPORT ──────────────────────────────────────
    if report_type in ("inventory", "low_stock"):
        rows = (
            svc.get_low_stock_rows(location_id=location_id)
            if report_type == "low_stock"
            else svc.get_stock_rows(location_id=location_id)
        )

        heading = (
            "Items Below Minimum Stock Threshold"
            if report_type == "low_stock"
            else "Current Stock Levels"
        )
        elements.append(Paragraph(heading, styles["Heading2"]))

        if not rows:
            elements.append(Paragraph("No data found for the selected criteria.", styles["Normal"]))
        else:
            def _status(r: dict) -> str:
                if r["current_stock"] <= 0:
                    return "CRITICAL"
                if r["current_stock"] <= r["min_stock"]:
                    return "WARNING"
                return "HEALTHY"

            table_data = [["Item Name", "Category", "Unit", "Current Stock", "Min Required", "Status"]]
            for r in rows:
                table_data.append([
                    r["name"][:35],
                    r["category"],
                    r["unit"],
                    str(r["current_stock"]),
                    str(r["min_stock"]),
                    _status(r),
                ])
            t = Table(table_data, colWidths=[2.2*inch, 1*inch, 0.6*inch, 0.9*inch, 0.9*inch, 0.8*inch])
            t.setStyle(TableStyle(HEADER_STYLE))
            elements.append(t)

    # ── TRANSACTIONS REPORT ───────────────────────────────────────────────
    elif report_type == "transactions":
        elements.append(Paragraph("Recent Stock Transactions", styles["Heading2"]))
        rows = svc.get_transaction_rows(
            location_id=location_id,
            date_from=date_from,
            date_to=date_to,
        )
        if not rows:
            elements.append(Paragraph("No transactions found for the selected criteria.", styles["Normal"]))
        else:
            table_data = [["Date", "Location", "Item", "Open", "In", "Out", "Close", "By"]]
            for r in rows:
                table_data.append([
                    r["date"],
                    r["location"][:20],
                    r["item"][:25],
                    str(r["opening_stock"]),
                    str(r["received"]),
                    str(r["issued"]),
                    str(r["closing_stock"]),
                    r["entered_by"][:12],
                ])
            t = Table(table_data, colWidths=[
                0.75*inch, 1.4*inch, 1.5*inch,
                0.5*inch, 0.4*inch, 0.4*inch, 0.5*inch, 0.75*inch,
            ])
            t.setStyle(TableStyle(HEADER_STYLE))
            elements.append(t)
            elements.append(Paragraph(f"Showing {len(rows)} most recent transactions.", styles["Normal"]))

    # ── REQUISITIONS REPORT ───────────────────────────────────────────────
    elif report_type == "requisitions":
        elements.append(Paragraph("Requisitions Summary", styles["Heading2"]))

        stats = svc.get_requisition_stats(date_from=date_from, date_to=date_to)
        stat_data = [
            ["Metric", "Count"],
            ["Total", str(stats["total"])],
            ["Pending", str(stats["pending"])],
            ["Approved", str(stats["approved"])],
            ["Rejected", str(stats["rejected"])],
        ]
        st = Table(stat_data, colWidths=[2.5*inch, 1*inch])
        st.setStyle(TableStyle(HEADER_STYLE))
        elements.append(st)
        elements.append(Spacer(1, 0.2*inch))

        rows = svc.get_requisition_rows(date_from=date_from, date_to=date_to)
        if rows:
            elements.append(Paragraph("Requisition List", styles["Heading2"]))
            table_data = [["Req #", "Department", "Requested By", "Urgency", "Status", "Date"]]
            for r in rows:
                table_data.append([
                    r["requisition_number"],
                    r["department"],
                    r["requested_by"],
                    r["urgency"],
                    r["status"],
                    r["created_at"],
                ])
            t = Table(table_data, colWidths=[1.1*inch, 1*inch, 1.2*inch, 0.8*inch, 0.9*inch, 0.9*inch])
            t.setStyle(TableStyle(HEADER_STYLE))
            elements.append(t)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    filename = f"inviq_{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
