from pydantic import BaseModel, Field
from typing import List, Optional


class RequisitionItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0, description="Quantity requested")
    notes: Optional[str] = None


class CreateRequisitionRequest(BaseModel):
    location_id: int
    requested_by: Optional[str] = None  # Set server-side from current_user
    department: str = Field(min_length=2, max_length=100)
    urgency: str = Field(default="NORMAL", pattern="^(LOW|NORMAL|HIGH|EMERGENCY)$")
    items: List[RequisitionItemCreate] = Field(min_length=1)
    notes: Optional[str] = None


class ApproveRequest(BaseModel):
    approved_by: Optional[str] = None  # Set server-side from current_user
    item_adjustments: Optional[List[dict]] = None


class RejectRequest(BaseModel):
    rejected_by: Optional[str] = None  # Set server-side from current_user
    reason: str = Field(min_length=5, max_length=500)


class CancelRequest(BaseModel):
    cancelled_by: Optional[str] = None  # Set server-side from current_user
