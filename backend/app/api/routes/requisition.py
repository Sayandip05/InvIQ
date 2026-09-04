"""
Requisition API routes.

Routes receive pre-configured RequisitionService via FastAPI's Depends() system.
All routes are strictly org-scoped: users can only see/mutate their own
organization's requisitions.
"""

from fastapi import APIRouter, Depends, Request
from typing import Optional
from app.core.rate_limiter import limiter

from app.core.dependencies import (
    get_requisition_service,
    get_current_user,
    require_admin,
    require_staff,
    get_caller_org_id,
)
from app.core.exceptions import NotFoundError, AuthorizationError
from app.application.requisition_service import RequisitionService
from app.infrastructure.database.models import User
from app.api.schemas.requisition_schemas import (
    CreateRequisitionRequest,
    ApproveRequest,
    RejectRequest,
    CancelRequest,
)

router = APIRouter(prefix="/requisition", tags=["Requisition"])


def _caller_org_id(user: User) -> Optional[int]:
    """Return org_id for tenant-scoped operations using central dependency rule."""
    return get_caller_org_id(user)


def _has_location_access(user: User, target_location_id: int) -> bool:
    """Check if staff user is permitted to access this location."""
    raw = getattr(user, "location_ids", None)
    if not raw:
        return True
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            raw = [raw]
    if isinstance(raw, (list, set, tuple)):
        allowed_ids = set()
        for item in raw:
            try:
                allowed_ids.add(int(item))
            except (ValueError, TypeError):
                pass
        if not allowed_ids:
            return True
        return target_location_id in allowed_ids
    return True


@router.post("/create")
@limiter.limit("20/minute")
def create_requisition(
    request: Request,
    body: CreateRequisitionRequest,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(require_staff),
):
    org_id = _caller_org_id(current_user)

    if current_user.role == "staff" and not _has_location_access(current_user, body.location_id):
        raise AuthorizationError(f"Staff account is not authorized to create requisitions for Location #{body.location_id}")

    items_data = [
        {"item_id": item.item_id, "quantity": item.quantity, "notes": item.notes}
        for item in body.items
    ]

    return service.create_requisition(
        location_id=body.location_id,
        requested_by=str(current_user.username),
        department=body.department,
        urgency=body.urgency,
        items=items_data,
        notes=body.notes,
        org_id=org_id,
    )




@router.get("/list")
def list_requisitions(
    status: Optional[str] = None,
    location_id: Optional[int] = None,
    requested_by: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(get_current_user),
):
    if limit > 100:
        limit = 100
    org_id = _caller_org_id(current_user)
    data = service.list_requisitions(
        status=status, location_id=location_id, requested_by=requested_by, org_id=org_id
    )
    total = len(data)
    paginated = data[skip : skip + limit]
    return {
        "success": True,
        "data": paginated,
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total,
        },
    }


@router.get("/stats")
def get_requisition_stats(
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(get_current_user),
):
    org_id = _caller_org_id(current_user)
    stats = service.get_stats(org_id=org_id)
    return {"success": True, "data": stats}


@router.get("/{requisition_id}")
def get_requisition(
    requisition_id: int,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(get_current_user),
):
    org_id = _caller_org_id(current_user)
    data = service.get_requisition(requisition_id, org_id=org_id)
    if not data:
        raise NotFoundError("Requisition", requisition_id)
    return {"success": True, "data": data}


@router.put("/{requisition_id}/approve")
@limiter.limit("10/minute")
def approve_requisition(
    requisition_id: int,
    request: Request,
    body: ApproveRequest,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(require_admin),
):
    org_id = _caller_org_id(current_user)
    return service.approve_requisition(
        requisition_id=requisition_id,
        approved_by=str(current_user.username),
        item_adjustments=body.item_adjustments,
        org_id=org_id,
    )


@router.put("/{requisition_id}/reject")
@limiter.limit("10/minute")
def reject_requisition(
    requisition_id: int,
    request: Request,
    body: RejectRequest,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(require_admin),
):
    org_id = _caller_org_id(current_user)
    return service.reject_requisition(
        requisition_id=requisition_id,
        rejected_by=str(current_user.username),
        reason=body.reason,
        org_id=org_id,
    )


@router.put("/{requisition_id}/cancel")
@limiter.limit("10/minute")
def cancel_requisition(
    requisition_id: int,
    request: Request,
    body: CancelRequest,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(require_staff),
):
    org_id = _caller_org_id(current_user)
    return service.cancel_requisition(
        requisition_id=requisition_id,
        cancelled_by=str(current_user.username),
        org_id=org_id,
    )


@router.put("/{requisition_id}/fulfill")
@limiter.limit("10/minute")
def fulfill_requisition(
    requisition_id: int,
    request: Request,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(require_staff),
):
    """Mark an approved requisition as fulfilled upon stock dispatch / physical delivery."""
    org_id = _caller_org_id(current_user)
    return service.fulfill_requisition(
        requisition_id=requisition_id,
        fulfilled_by=str(current_user.username),
        org_id=org_id,
    )

