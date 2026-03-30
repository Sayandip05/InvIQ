"""
Vendor API — Excel delivery upload, upload history, and template download.

Vendors can upload Excel files containing delivery data.
The system parses rows, matches item names, and creates inventory transactions.
"""

import logging
from io import BytesIO
from fastapi import APIRouter, Depends, UploadFile, File, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.rate_limiter import limiter
from app.core.exceptions import ValidationError, AuthorizationError
from app.infrastructure.database.models import User, Location
from app.application.vendor_service import VendorService

logger = logging.getLogger("smart_inventory.vendor")

router = APIRouter(prefix="/vendor", tags=["Vendor"])


def _require_vendor_role(current_user: User) -> None:
    """Ensure user has vendor, admin, or super_admin role."""
    if current_user.role not in {"vendor", "admin", "super_admin"}:
        raise AuthorizationError("Vendor access required")


# ── POST /vendor/upload-delivery ───────────────────────────────────────────

@router.post("/upload-delivery")
@limiter.limit("10/minute")
def upload_delivery(
    request: Request,
    location_id: int = Query(..., description="Target location for this delivery"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an Excel delivery manifest.

    The file should have columns: item_name, quantity_received, delivery_date (optional), notes (optional).
    Each row creates an inventory transaction (received stock).
    """
    _require_vendor_role(current_user)

    # Validate file type
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise ValidationError("Only .xlsx or .xls files are accepted")

    # Validate location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise ValidationError(f"Location {location_id} not found")

    # Check vendor location access (if location_ids is set)
    if current_user.location_ids and location_id not in current_user.location_ids:
        raise AuthorizationError("You don't have access to this location")

    # Read file
    content = file.file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB max
        raise ValidationError("File size must be under 5MB")

    service = VendorService(db)
    result = service.parse_and_process_excel(
        file_content=content,
        filename=file.filename,
        location_id=location_id,
        vendor_user_id=current_user.id,
        org_id=current_user.org_id,
    )

    return result


# ── GET /vendor/my-uploads ─────────────────────────────────────────────────

@router.get("/my-uploads")
def get_my_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload history for the current vendor."""
    _require_vendor_role(current_user)

    service = VendorService(db)
    uploads = service.get_uploads_for_vendor(current_user.id)

    return {
        "success": True,
        "data": uploads,
        "total": len(uploads),
    }


# ── GET /vendor/template ──────────────────────────────────────────────────

@router.get("/template")
def download_template(
    current_user: User = Depends(get_current_user),
):
    """Download a blank Excel template for vendor deliveries."""
    _require_vendor_role(current_user)

    try:
        import openpyxl
    except ImportError:
        raise ValidationError("openpyxl is not installed on the server")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Delivery Template"

    # Header row
    headers = ["item_name", "quantity_received", "delivery_date", "notes"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = openpyxl.styles.Font(bold=True)

    # Example row
    ws.cell(row=2, column=1, value="Paracetamol 500mg")
    ws.cell(row=2, column=2, value=100)
    ws.cell(row=2, column=3, value="2026-03-28")
    ws.cell(row=2, column=4, value="Order #12345")

    # Column widths
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 30

    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    wb.close()

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=delivery_template.xlsx"},
    )
