"""
Admin Dashboard API — Super Admin endpoints for platform management.

Provides overview stats, user management summaries, and audit trail
access for the platform owner's dashboard.
"""

import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session

from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from app.core.rate_limiter import limiter
from app.core.dependencies import get_db, require_admin

from app.infrastructure.database.models import User, AuditLog, Organization, Location
from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.database.audit_repo import AuditRepository
from app.application.report_service import ReportService
from app.core.exceptions import NotFoundError, DuplicateError, AuthorizationError

logger = logging.getLogger("smart_inventory.admin")

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])



class UpdatePharmacyOrganizationRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    dl_number: Optional[str] = None
    settings: Optional[dict] = None


# ── GET & PUT /admin/organization ──────────────────────────────────────────


@router.get("/organization", response_model=dict)
def get_pharmacy_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get the current pharmacy owner's organization profile & branch metrics."""
    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    org_id = current_user.org_id
    if not org_id:
        raise NotFoundError("Organization", "default")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization", org_id)

    locations = db.query(Location).filter(Location.org_id == org_id).all()

    return {
        "success": True,
        "data": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "address": org.address,
            "phone": org.phone,
            "email": org.email,
            "gstin": org.gstin,
            "dl_number": org.dl_number,
            "settings": org.settings or {},
            "is_active": org.is_active,
            "created_at": str(org.created_at) if org.created_at else None,
            "branches": [
                {
                    "id": loc.id,
                    "name": loc.name,
                    "type": loc.type,
                    "region": loc.region,
                    "address": loc.address,
                    "phone": loc.phone,
                    "pincode": loc.pincode,
                    "radius_meters": loc.radius_meters,
                    "is_active": loc.is_active,
                }
                for loc in locations
            ],
            "total_branches": len(locations),
            "active_branches": len([l for l in locations if l.is_active]),
        },
    }


@router.put("/organization", response_model=dict)
def update_pharmacy_organization(
    body: UpdatePharmacyOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update pharmacy organization profile (name, address, phone, GSTIN, DL number, settings)."""
    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    org_id = current_user.org_id
    if not org_id:
        raise NotFoundError("Organization", "default")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization", org_id)

    if body.name is not None and body.name.strip():
        new_name = body.name.strip()
        existing = db.query(Organization).filter(Organization.name == new_name, Organization.id != org_id).first()
        if existing:
            raise DuplicateError(f"An organization with the name '{new_name}' already exists")
        org.name = new_name

    if body.address is not None:
        org.address = body.address.strip() if body.address else None
    if body.phone is not None:
        org.phone = body.phone.strip() if body.phone else None
    if body.email is not None:
        org.email = body.email.strip() if body.email else None
    if body.gstin is not None:
        org.gstin = body.gstin.strip() if body.gstin else None
    if body.dl_number is not None:
        org.dl_number = body.dl_number.strip() if body.dl_number else None
    if body.settings is not None:
        merged = dict(org.settings or {})
        merged.update(body.settings)
        org.settings = merged

    db.commit()
    db.refresh(org)

    # Asynchronously index onboarding context into Vector Memory for AI assistant personalization
    try:
        from app.workers.tasks import sync_onboarding_context_task
        primary_counter = (org.settings or {}).get("primary_counter_name", "Main Market Counter")
        plan_type = (org.settings or {}).get("plan_type", org.plan or "single_pharmacy")
        sync_onboarding_context_task.delay(
            org_id=org.id,
            user_id=current_user.id,
            full_name=current_user.full_name or current_user.username,
            pharmacy_name=org.name,
            primary_counter=primary_counter,
            plan_type=plan_type,
            extra_settings=org.settings or {},
        )
    except Exception as e:
        logger.warning("Could not dispatch onboarding vector indexing: %s", e)

    return {
        "success": True,
        "message": "Pharmacy organization profile updated successfully",
        "data": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "address": org.address,
            "phone": org.phone,
            "email": org.email,
            "gstin": org.gstin,
            "dl_number": org.dl_number,
            "settings": org.settings or {},
        },
    }



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
    from app.application.cache_service import cache_get, cache_set
    cache_key = f"ref:admin_overview:{current_user.org_id or 0}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    target_org_id = current_user.org_id
    if target_org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    # Consolidated single-query aggregation across roles and active statuses scoped to tenant org
    from sqlalchemy import func
    query = db.query(User.role, User.is_active, func.count(User.id))
    if target_org_id is not None:
        query = query.filter(User.org_id == target_org_id)
    role_active_counts = query.group_by(User.role, User.is_active).all()

    total_users = 0
    active_users = 0
    inactive_users = 0
    role_counts = {"admin": 0, "staff": 0, "vendor": 0}

    for role, is_active, count in role_active_counts:
        total_users += count
        if is_active:
            active_users += count
        else:
            inactive_users += count
        if role in role_counts:
            role_counts[role] += count
        else:
            role_counts[role] = count

    # Recent signups scoped to tenant org (last 5)
    recent_users = user_repo.get_all_filtered(org_id=target_org_id, limit=5)
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

    # Recent audit events scoped to tenant org
    recent_events = audit_repo.get_recent(org_id=target_org_id, limit=10)
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

    res = {
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
    cache_set(cache_key, res, ttl=30)
    return res


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
    Scoped strictly by organization for tenant admins.
    """
    target_org_id = current_user.org_id
    if target_org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    audit_repo = AuditRepository(db)
    logs = audit_repo.get_filtered(
        username=username,
        action=action,
        resource_type=resource_type,
        org_id=target_org_id,
        limit=limit,
    )

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
    Detailed user summary scoped by tenant organization for admin user management.
    """
    target_org_id = current_user.org_id
    if target_org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    user_repo = UserRepository(db)
    all_users = user_repo.get_all_filtered(org_id=target_org_id, limit=1000)


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



# ── SUPPLIER / DISTRIBUTOR MANAGEMENT ─────────────────────────────────────

import secrets
from pydantic import BaseModel, Field, EmailStr
from app.core.security import hash_password, validate_password_strength
from app.core.exceptions import ValidationError, NotFoundError
from app.infrastructure.database.models import VendorUpload, VendorInvoice


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200, description="Distributor / wholesaler business name")
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="Explicit secure password or None to auto-generate a secure random temporary credential")
    phone: Optional[str] = None
    location_ids: Optional[list] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location_ids: Optional[list] = None
    is_active: Optional[bool] = None


@router.get("/suppliers", response_model=dict)
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List all medicine distributors / suppliers for the current medical store organization.
    """
    query = db.query(User).filter(User.role == "vendor")
    if current_user.org_id:
        query = query.filter(User.org_id == current_user.org_id)

    vendors = query.order_by(User.created_at.desc()).all()

    data = []
    for v in vendors:
        uploads_count = db.query(VendorUpload).filter(VendorUpload.vendor_user_id == v.id).count()
        invoices_count = db.query(VendorInvoice).filter(VendorInvoice.vendor_user_id == v.id).count()
        data.append({
            "id": v.id,
            "name": v.full_name or v.username,
            "username": v.username,
            "email": v.email,
            "role": v.role,
            "location_ids": v.location_ids or [],
            "is_active": v.is_active,
            "total_uploads": uploads_count,
            "total_invoices": invoices_count,
            "last_login_at": str(v.last_login_at) if v.last_login_at else None,
            "created_at": str(v.created_at) if v.created_at else None,
        })

    return {
        "success": True,
        "data": data,
        "total": len(data),
    }


@router.post("/suppliers", response_model=dict)
def create_supplier(
    body: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Add a new medicine distributor / supplier to the medical store organization.
    Requires an explicit strong password or auto-generates a secure temporary password.
    """
    # Check duplicate username or email
    existing_user = db.query(User).filter(
        (User.username == body.username) | (User.email == body.email)
    ).first()
    if existing_user:
        raise ValidationError("A supplier with this username or email already exists")

    if body.password:
        is_valid, msg = validate_password_strength(body.password)
        if not is_valid:
            raise ValidationError(f"Password security policy violation: {msg}")
        pwd = body.password
        generated_temp_password = None
    else:
        pwd = f"Sup!{secrets.token_urlsafe(12)}8#"
        generated_temp_password = pwd

    # Validate location_ids if supplied
    loc_ids = body.location_ids or []
    if loc_ids:
        if current_user.org_id is None:
            raise AuthorizationError("User is not assigned to an organization")
        valid_locs = db.query(Location.id).filter(
            Location.id.in_(loc_ids),
            Location.org_id == current_user.org_id,
        ).all()
        valid_set = {loc[0] for loc in valid_locs}
        invalid_ids = [lid for lid in loc_ids if lid not in valid_set]
        if invalid_ids:
            raise ValidationError(f"Invalid location ID(s): {invalid_ids}. Locations must belong to your organization.")

    supplier = User(
        org_id=current_user.org_id,
        username=body.username,
        email=body.email,
        full_name=body.name,
        hashed_password=hash_password(pwd),
        role="vendor",
        location_ids=loc_ids,
        is_active=True,
        is_verified=True,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    res_data = {
        "id": supplier.id,
        "name": supplier.full_name,
        "username": supplier.username,
        "email": supplier.email,
        "role": supplier.role,
        "is_active": supplier.is_active,
        "created_at": str(supplier.created_at) if supplier.created_at else None,
    }
    if generated_temp_password:
        res_data["temporary_password"] = generated_temp_password

    return {
        "success": True,
        "message": f"Supplier '{supplier.full_name}' created successfully",
        "data": res_data,
    }



@router.put("/suppliers/{supplier_id}", response_model=dict)
def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update details for a specific medicine supplier.
    """
    query = db.query(User).filter(User.id == supplier_id, User.role == "vendor")
    if current_user.org_id:
        query = query.filter(User.org_id == current_user.org_id)

    supplier = query.first()
    if not supplier:
        raise NotFoundError(f"Supplier with ID {supplier_id} not found")

    if body.name is not None:
        supplier.full_name = body.name
    if body.email is not None:
        supplier.email = body.email
    if body.location_ids is not None:
        if body.location_ids:
            if current_user.org_id is None:
                raise AuthorizationError("User is not assigned to an organization")
            valid_locs = db.query(Location.id).filter(
                Location.id.in_(body.location_ids),
                Location.org_id == current_user.org_id,
            ).all()
            valid_set = {loc[0] for loc in valid_locs}
            invalid_ids = [lid for lid in body.location_ids if lid not in valid_set]
            if invalid_ids:
                raise ValidationError(f"Invalid location ID(s): {invalid_ids}. Locations must belong to your organization.")
        supplier.location_ids = body.location_ids
    if body.is_active is not None:
        supplier.is_active = body.is_active

    db.commit()
    db.refresh(supplier)

    return {
        "success": True,
        "message": f"Supplier '{supplier.full_name}' updated successfully",
        "data": {
            "id": supplier.id,
            "name": supplier.full_name,
            "username": supplier.username,
            "email": supplier.email,
            "is_active": supplier.is_active,
            "location_ids": supplier.location_ids,
        },
    }



@router.delete("/suppliers/{supplier_id}", response_model=dict)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Deactivate or remove a medicine supplier.
    """
    query = db.query(User).filter(User.id == supplier_id, User.role == "vendor")
    if current_user.org_id:
        query = query.filter(User.org_id == current_user.org_id)

    supplier = query.first()
    if not supplier:
        raise NotFoundError(f"Supplier with ID {supplier_id} not found")

    supplier.is_active = False
    db.commit()

    return {
        "success": True,
        "message": f"Supplier '{supplier.full_name}' deactivated successfully",
    }



# ── GET /admin/reports/generate & /admin/reports/export ────────────────────


@router.get("/reports/generate")
@router.get("/reports/export")
@limiter.limit("10/minute")
def generate_pdf_report(
    request: Request,
    report_type: str = Query("inventory", description="inventory | requisitions | low_stock | monthly_sales"),
    location_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):

    """
    Generate and stream a PDF report.
    Supports: inventory, requisitions, low_stock, monthly_sales

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

    # ── Tenant boundary check ──────────────────────────────────────────
    caller_org_id = current_user.org_id
    if caller_org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    # Validate location ownership if filtered
    if location_id is not None and caller_org_id is not None:
        loc = db.query(Location).filter(Location.id == location_id, Location.org_id == caller_org_id).first()
        if not loc:
            raise NotFoundError("Location", location_id)

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
        "inventory":     "Inventory Stock Report",
        "requisitions":  "Requisitions Report",
        "low_stock":     "Low Stock Alert Report",
        "monthly_sales": "Monthly Sales & Profit Report",
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
            svc.get_low_stock_rows(location_id=location_id, org_id=caller_org_id)
            if report_type == "low_stock"
            else svc.get_stock_rows(location_id=location_id, org_id=caller_org_id)
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

    # ── REQUISITIONS REPORT ───────────────────────────────────────────────
    elif report_type == "requisitions":
        elements.append(Paragraph("Requisitions Summary", styles["Heading2"]))

        stats = svc.get_requisition_stats(date_from=date_from, date_to=date_to, org_id=caller_org_id)
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

        rows = svc.get_requisition_rows(date_from=date_from, date_to=date_to, org_id=caller_org_id)
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

    # ── MONTHLY SALES REPORT ──────────────────────────────────────────────
    elif report_type == "monthly_sales":
        # Extract year and month from date_from (e.g. "2026-08" or "2026-08-01") or default to current
        now = datetime.now(timezone.utc)
        target_year = now.year
        target_month = now.month
        if date_from:
            try:
                parts = date_from.split("-")
                target_year = int(parts[0])
                target_month = int(parts[1])
            except Exception:
                pass

        month_label = f"{target_year:04d}-{target_month:02d}"
        elements.append(Paragraph(f"Monthly Financial Performance ({month_label})", styles["Heading2"]))

        summary = svc.get_monthly_sales_summary(
            org_id=caller_org_id or 1,
            year=target_year,
            month=target_month,
        )

        sales_data = [
            ["Financial Metric", "Value (INR)"],
            ["Total Customer Bills (Sessions)", str(summary.get("session_count", 0))],
            ["Gross Sales (MRP Total)", f"Rs. {summary.get('gross_total', 0.0):,.2f}"],
            ["Total Customer Discounts Given", f"Rs. {summary.get('discount_amount', 0.0):,.2f}"],
            ["Net Realized Revenue", f"Rs. {summary.get('net_total', 0.0):,.2f}"],
            ["Medication Purchase Cost (COGS)", f"Rs. {summary.get('purchase_cost', 0.0):,.2f}"],
            ["Gross Profit", f"Rs. {summary.get('gross_profit', 0.0):,.2f}"],
            ["Gross Profit Margin", f"{summary.get('margin_pct', 0.0):.2f}%"],
        ]
        st = Table(sales_data, colWidths=[3.2 * inch, 2.2 * inch])
        st.setStyle(TableStyle(HEADER_STYLE))
        elements.append(st)

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.seek(0)

    filename = f"inviq_{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf"
    response_headers = {"Content-Disposition": f"attachment; filename={filename}"}

    # Upload generated report to Azure Blob Storage for cloud archiving if available
    try:
        from app.infrastructure.storage.azure_blob_storage import get_storage_service
        storage = get_storage_service()
        if storage.is_available:
            now_dt = datetime.now(timezone.utc)
            blob_path = f"reports/{caller_org_id or 'global'}/{now_dt.year}/{now_dt.month:02d}/{filename}"
            blob_url = storage.upload_file(
                file_bytes=pdf_bytes,
                blob_name=blob_path,
                content_type="application/pdf",
            )
            if blob_url:
                sas_url = storage.generate_sas_url(blob_path)
                response_headers["X-Report-Blob-Path"] = blob_path
                response_headers["X-Report-Blob-Url"] = sas_url or blob_url
                logger.info("Archived admin report PDF in Azure Blob Storage: %s", blob_path)
    except Exception as storage_err:
        logger.warning("Failed to archive report in Azure Blob Storage: %s", storage_err)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers=response_headers,
    )


# ── Discount Settings ─────────────────────────────────────────────────────────


class TieredSlab(BaseModel):
    min_bill:     float = Field(ge=0, description="Minimum bill total for this slab (₹)")
    max_bill:     Optional[float] = Field(default=None, description="Maximum bill total (₹); null = no ceiling")
    discount_pct: float = Field(ge=0.0, le=100.0, description="Discount percentage for this slab")


class DiscountSettingsRequest(BaseModel):
    discount_model:         Literal["flat", "tiered", "none"]
    flat_discount_pct:      float = Field(default=0.0, ge=0.0, le=100.0)
    tiered_discount_config: Optional[List[TieredSlab]] = None
    manual_discount_cap_pct: float = Field(default=20.0, ge=0.0, le=100.0)


@router.get("/discount-settings", response_model=dict)
def get_discount_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Return the current discount policy for this organisation."""
    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organisation")
    org = db.query(Organization).filter(Organization.id == current_user.org_id).first()
    if not org:
        raise NotFoundError("Organisation", current_user.org_id)

    settings = org.settings or {}
    return {
        "success": True,
        "data": {
            "discount_model":          settings.get("discount_model", "none"),
            "flat_discount_pct":       settings.get("flat_discount_pct", 0.0),
            "tiered_discount_config":  settings.get("tiered_discount_config", []),
            "manual_discount_cap_pct": settings.get("manual_discount_cap_pct", 20.0),
        },
    }


@router.put("/discount-settings", response_model=dict)
def update_discount_settings(
    body: DiscountSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Save discount policy into org.settings.
    Validates tiered slabs before persisting.
    """
    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organisation")
    org = db.query(Organization).filter(Organization.id == current_user.org_id).first()
    if not org:
        raise NotFoundError("Organisation", current_user.org_id)

    # Build the config dict from the request
    config: dict = {
        "discount_model":          body.discount_model,
        "flat_discount_pct":       body.flat_discount_pct,
        "manual_discount_cap_pct": body.manual_discount_cap_pct,
        "tiered_discount_config":  [
            {
                "min_bill":     s.min_bill,
                "max_bill":     s.max_bill,
                "discount_pct": s.discount_pct,
            }
            for s in (body.tiered_discount_config or [])
        ],
    }

    # Validate using the discount service
    from app.application.discount_service import validate_discount_config
    errors = validate_discount_config(config)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    # Merge into org.settings (preserves other settings keys)
    merged = dict(org.settings or {})
    merged.update(config)
    org.settings = merged
    db.commit()

    logger.info(
        "Discount settings updated | org=%s model=%s",
        current_user.org_id, body.discount_model,
    )
    return {
        "success": True,
        "message": "Discount policy saved successfully",
        "data": config,
    }


# ── Monthly Sales & Profit Report ─────────────────────────────────────────────


@router.get("/reports/monthly-sales", response_model=dict)
def get_monthly_sales_report(
    year:  int = Query(..., ge=2020, le=2100, description="Calendar year, e.g. 2026"),
    month: int = Query(..., ge=1,    le=12,   description="Calendar month 1–12"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Monthly Sales & Profit summary for the selected calendar month.

    Reads from Redis monthly sales cache (fast path).
    Falls back to DB aggregate on billing_sessions when Redis is cold/empty.
    Report includes: gross sales, discounts given, net revenue, purchase cost,
    gross profit, and margin percentage.
    """
    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organisation")

    org_id    = current_user.org_id
    month_key = f"{year:04d}-{month:02d}"

    # ── 1. Try Redis cache (fast path) ──────────────────────────────────
    summary = None
    try:
        from app.infrastructure.cache.redis_client import get_redis, is_redis_available
        r = get_redis()
        if r and is_redis_available():
            import json
            raw = r.hgetall(f"sales:{org_id}:{month_key}")
            if raw:
                summary = {
                    "month":           month_key,
                    "session_count":   int(raw.get(b"session_count", 0) or raw.get("session_count", 0)),
                    "gross_total":     float(raw.get(b"gross_total",    0) or raw.get("gross_total",    0)),
                    "discount_amount": float(raw.get(b"discount_amount",0) or raw.get("discount_amount",0)),
                    "net_total":       float(raw.get(b"net_total",      0) or raw.get("net_total",      0)),
                    "purchase_cost":   float(raw.get(b"purchase_cost",  0) or raw.get("purchase_cost",  0)),
                }
                net    = summary["net_total"]
                cost   = summary["purchase_cost"]
                profit = round(net - cost, 2)
                summary["gross_profit"] = profit
                summary["margin_pct"]   = round((profit / net * 100) if net > 0 else 0.0, 2)
    except Exception as e:
        logger.warning("Redis monthly sales cache read failed: %s", e)

    # ── 2. DB fallback ──────────────────────────────────────────────────
    if summary is None:
        try:
            from app.infrastructure.database.billing_repo import BillingRepository
            billing_repo = BillingRepository(db)
            summary = billing_repo.get_monthly_aggregate(org_id=org_id, year=year, month=month)
        except Exception as e:
            logger.error("Monthly sales DB aggregate failed: %s", e)
            summary = {
                "month":           month_key,
                "session_count":   0,
                "gross_total":     0.0,
                "discount_amount": 0.0,
                "net_total":       0.0,
                "purchase_cost":   0.0,
                "gross_profit":    0.0,
                "margin_pct":      0.0,
            }

    return {"success": True, "data": summary}

