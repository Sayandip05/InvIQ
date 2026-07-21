"""
Requisition API routes.

Routes receive pre-configured RequisitionService via FastAPI's Depends() system.
"""

from fastapi import APIRouter, Depends, Request
from typing import Optional
from app.core.rate_limiter import limiter

from app.core.dependencies import (
    get_requisition_service,
    get_current_user,
    get_optional_user,
    require_staff,
    require_manager,
)
from app.core.exceptions import NotFoundError
from app.application.requisition_service import RequisitionService
from app.infrastructure.database.models import User
from app.api.schemas.requisition_schemas import (
    CreateRequisitionRequest,
    ApproveRequest,
    RejectRequest,
    CancelRequest,
)

router = APIRouter(prefix="/requisition", tags=["Requisition"])


@router.post("/create")
@limiter.limit("20/minute")
def create_requisition(
    request: Request,
    body: CreateRequisitionRequest,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(require_staff),
):
    items_data = [
        {"item_id": item.item_id, "quantity": item.quantity, "notes": item.notes}
        for item in body.items
    ]

    return service.create_requisition(
        location_id=body.location_id,
        requested_by=current_user.username,
        department=body.department,
        urgency=body.urgency,
        items=items_data,
        notes=body.notes,
    )


@router.get("/list")
def list_requisitions(
    status: Optional[str] = None,
    location_id: Optional[int] = None,
    requested_by: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if limit > 100:
        limit = 100
    data = service.list_requisitions(
        status=status, location_id=location_id, requested_by=requested_by
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
    current_user: Optional[User] = Depends(get_optional_user),
):
    stats = service.get_stats()
    return {"success": True, "data": stats}


@router.get("/{requisition_id}")
def get_requisition(
    requisition_id: int,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: Optional[User] = Depends(get_optional_user),
):
    data = service.get_requisition(requisition_id)
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
    current_user: User = Depends(require_manager),
):
    return service.approve_requisition(
        requisition_id=requisition_id,
        approved_by=str(current_user.username),
        item_adjustments=body.item_adjustments,
    )


@router.put("/{requisition_id}/reject")
@limiter.limit("10/minute")
def reject_requisition(
    requisition_id: int,
    request: Request,
    body: RejectRequest,
    service: RequisitionService = Depends(get_requisition_service),
    current_user: User = Depends(require_manager),
):
    return service.reject_requisition(
        requisition_id=requisition_id,
        rejected_by=str(current_user.username),
        reason=body.reason,
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
    return service.cancel_requisition(
        requisition_id=requisition_id,
        cancelled_by=str(current_user.username),
    )
