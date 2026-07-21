from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class TransactionItem(BaseModel):
    item_id: int
    received: int = Field(ge=0, description="Quantity received (must be >= 0)")
    issued: int = Field(ge=0, description="Quantity issued/used (must be >= 0)")
    notes: Optional[str] = None
    # Batch-level pharmacy fields — filled only on inbound deliveries (received > 0)
    batch_number: Optional[str] = Field(default=None, max_length=50, description="Batch/lot number of this delivery")
    expiry_date: Optional[date] = Field(default=None, description="Expiry date of this batch")


class SingleTransactionRequest(BaseModel):
    location_id: int
    item_id: int
    date: date
    received: int = Field(ge=0)
    issued: int = Field(ge=0)
    notes: Optional[str] = None
    entered_by: Optional[str] = "staff"
    # Batch-level pharmacy fields — filled only on inbound deliveries (received > 0)
    batch_number: Optional[str] = Field(default=None, max_length=50, description="Batch/lot number of this delivery")
    expiry_date: Optional[date] = Field(default=None, description="Expiry date of this batch")


class BulkTransactionRequest(BaseModel):
    location_id: int
    date: date
    items: List[TransactionItem]
    entered_by: Optional[str] = "staff"


class CreateLocationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    type: str = Field(min_length=2, max_length=50)
    region: str = Field(min_length=2, max_length=100)
    address: Optional[str] = None


class CreateItemRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=100)
    unit: str = Field(min_length=1, max_length=50)
    lead_time_days: int = Field(ge=1, le=365)
    min_stock: int = Field(ge=0)
    # Product-level pharmacy field (all units of this product share the same storage requirement)
    storage_temp: Optional[str] = Field(default="ambient", pattern="^(ambient|cold_chain)$", description="Storage temperature requirement")


class ResetDataRequest(BaseModel):
    confirm: bool = False
