from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from app.database.connection import get_db
from app.services.requisition_service import RequisitionService

router = APIRouter(prefix="/requisition", tags=["Requisition"])


# ─── Request Models ───

class RequisitionItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0, description="Quantity requested")
    notes: Optional[str] = None


class CreateRequisitionRequest(BaseModel):
    location_id: int
    requested_by: str = Field(min_length=2, max_length=100)
    department: str = Field(min_length=2, max_length=100)
    urgency: str = Field(default="NORMAL", pattern="^(LOW|NORMAL|HIGH|EMERGENCY)$")
    items: List[RequisitionItemCreate] = Field(min_length=1)
    notes: Optional[str] = None


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=2, max_length=100)
    item_adjustments: Optional[List[dict]] = None  # [{"item_id": 1, "quantity_approved": 40}]


class RejectRequest(BaseModel):
    rejected_by: str = Field(min_length=2, max_length=100)
    reason: str = Field(min_length=5, max_length=500)


class CancelRequest(BaseModel):
    cancelled_by: str = Field(min_length=2, max_length=100)


# ─── Endpoints ───

@router.post("/create")
def create_requisition(
    request: CreateRequisitionRequest,
    db: Session = Depends(get_db),
):
    """Raise a new stock-out requisition (Department Staff)."""
    items_data = [
        {
            "item_id": item.item_id,
            "quantity": item.quantity,
            "notes": item.notes,
        }
        for item in request.items
    ]

    result = RequisitionService.create_requisition(
        db=db,
        location_id=request.location_id,
        requested_by=request.requested_by,
        department=request.department,
        urgency=request.urgency,
        items=items_data,
        notes=request.notes,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/list")
def list_requisitions(
    status: Optional[str] = None,
    location_id: Optional[int] = None,
    requested_by: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all requisitions (filter by status, location, or requester)."""
    data = RequisitionService.list_requisitions(
        db=db,
        status=status,
        location_id=location_id,
        requested_by=requested_by,
    )
    return {"success": True, "data": data, "count": len(data)}


@router.get("/stats")
def get_requisition_stats(db: Session = Depends(get_db)):
    """Get summary counts for the requisition dashboard."""
    stats = RequisitionService.get_stats(db)
    return {"success": True, "data": stats}


@router.get("/{requisition_id}")
def get_requisition(requisition_id: int, db: Session = Depends(get_db)):
    """Get full details of a single requisition."""
    data = RequisitionService.get_requisition(db, requisition_id)
    if not data:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return {"success": True, "data": data}


@router.put("/{requisition_id}/approve")
def approve_requisition(
    requisition_id: int,
    request: ApproveRequest,
    db: Session = Depends(get_db),
):
    """Approve a pending requisition and auto-deduct stock (Store Manager)."""
    result = RequisitionService.approve_requisition(
        db=db,
        requisition_id=requisition_id,
        approved_by=request.approved_by,
        item_adjustments=request.item_adjustments,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.put("/{requisition_id}/reject")
def reject_requisition(
    requisition_id: int,
    request: RejectRequest,
    db: Session = Depends(get_db),
):
    """Reject a pending requisition with a reason (Store Manager)."""
    result = RequisitionService.reject_requisition(
        db=db,
        requisition_id=requisition_id,
        rejected_by=request.rejected_by,
        reason=request.reason,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.put("/{requisition_id}/cancel")
def cancel_requisition(
    requisition_id: int,
    request: CancelRequest,
    db: Session = Depends(get_db),
):
    """Cancel own pending requisition (Department Staff)."""
    result = RequisitionService.cancel_requisition(
        db=db,
        requisition_id=requisition_id,
        cancelled_by=request.cancelled_by,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
