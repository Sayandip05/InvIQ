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
    phone: Optional[str] = None
    pincode: Optional[str] = None
    radius_meters: Optional[int] = 500


class UpdateLocationRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    type: Optional[str] = Field(default=None, min_length=2, max_length=50)
    region: Optional[str] = Field(default=None, min_length=2, max_length=100)
    address: Optional[str] = None
    phone: Optional[str] = None
    pincode: Optional[str] = None
    radius_meters: Optional[int] = Field(default=None, ge=50, le=50000)
    is_active: Optional[bool] = None



class CreateItemRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=100)
    unit: str = Field(min_length=1, max_length=50, description="Base indivisible atomic unit, e.g. tablet, capsule, ml, vial")
    barcode: Optional[str] = Field(default=None, max_length=50, description="Barcode or EAN-13")
    strength: Optional[str] = Field(default=None, max_length=50, description="Dosage strength, e.g. 500mg, 10ml")
    mrp: Optional[float] = Field(default=0.0, ge=0.0, description="Maximum Retail Price (MRP) per base unit")
    purchase_rate: Optional[float] = Field(default=0.0, ge=0.0, description="Purchase rate per base unit")
    lead_time_days: int = Field(default=2, ge=1, le=365)
    min_stock: int = Field(default=10, ge=0, description="Safety threshold in base units")
    # Product-level pharmacy field (all units of this product share the same storage requirement)
    storage_temp: Optional[str] = Field(default="ambient", pattern="^(ambient|cold_chain)$", description="Storage temperature requirement")


class UpdateItemRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    category: Optional[str] = Field(default=None, min_length=2, max_length=100)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=50)
    barcode: Optional[str] = Field(default=None, max_length=50)
    strength: Optional[str] = Field(default=None, max_length=50)
    mrp: Optional[float] = Field(default=None, ge=0.0)
    purchase_rate: Optional[float] = Field(default=None, ge=0.0)
    lead_time_days: Optional[int] = Field(default=None, ge=1, le=365)
    min_stock: Optional[int] = Field(default=None, ge=0)
    storage_temp: Optional[str] = Field(default=None, pattern="^(ambient|cold_chain)$")


class ResetDataRequest(BaseModel):
    confirm: bool = False


class ScanDispenseRequest(BaseModel):
    barcode: str = Field(min_length=1, max_length=100, description="Medicine barcode, package barcode, EAN-13, or numeric item ID")
    location_id: int = Field(gt=0, description="Counter / Branch location ID")
    quantity: int = Field(default=1, gt=0, description="Number of packages or base units to dispense")
    unit: Optional[str] = Field(default=None, description="Packaging unit to dispense (e.g. strip, box, tablet)")
    notes: Optional[str] = None


