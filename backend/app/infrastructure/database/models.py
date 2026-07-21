from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Text,
    ForeignKey,
    TIMESTAMP,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.infrastructure.database.connection import Base


# ── Multi-tenancy root ────────────────────────────────────────────────────

class Organization(Base):
    """Multi-tenancy root — every entity belongs to an org."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="organization")
    locations = relationship("Location", back_populates="organization")
    items = relationship("Item", back_populates="organization")


# ── Users ─────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(50), nullable=False, default="staff")
    location_ids = Column(JSON, default=[])  # Scoped locations for staff/vendor
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(TIMESTAMP, nullable=True)
    last_login_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="users")


# ── Inventory ─────────────────────────────────────────────────────────────

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)
    region = Column(String(100), nullable=False)
    address = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="locations")
    transactions = relationship("InventoryTransaction", back_populates="location")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    min_stock = Column(Integer, nullable=False)

    # ── Pharmacy-specific field ───────────────────────────────────────────
    # storage_temp is a PRODUCT-level attribute (Insulin is always cold_chain).
    # batch_number and expiry_date are BATCH-level — they belong on the
    # InventoryTransaction where each inbound delivery records its own batch.
    storage_temp = Column(String(20), nullable=False, default="ambient")  # ambient | cold_chain

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="items")
    transactions = relationship("InventoryTransaction", back_populates="item")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    date = Column(Date, nullable=False)
    opening_stock = Column(Integer, nullable=False)
    received = Column(Integer, nullable=False, default=0)
    issued = Column(Integer, nullable=False, default=0)
    closing_stock = Column(Integer, nullable=False)
    notes = Column(Text)
    entered_by = Column(String(100), default="system")

    # ── Batch-level pharmacy fields ──────────────────────────────────────
    # Each inbound delivery (received > 0) records which batch arrived and when
    # it expires — enabling multi-batch tracking per product.
    batch_number = Column(String(50), nullable=True, index=True)   # e.g. "BT-25-4821"
    expiry_date = Column(Date, nullable=True, index=True)           # expiry of this batch

    created_at = Column(TIMESTAMP, server_default=func.now())

    location = relationship("Location", back_populates="transactions")
    item = relationship("Item", back_populates="transactions")


# ── Chat ──────────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(100), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), default="New Conversation")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


# ── Requisitions ──────────────────────────────────────────────────────────

class Requisition(Base):
    __tablename__ = "requisitions"

    id = Column(Integer, primary_key=True, index=True)
    requisition_number = Column(String(50), unique=True, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    requested_by = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    urgency = Column(String(20), nullable=False, default="NORMAL")
    status = Column(String(20), nullable=False, default="PENDING")
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(TIMESTAMP, nullable=True)
    rejected_at = Column(TIMESTAMP, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    location = relationship("Location")
    items = relationship(
        "RequisitionItem", back_populates="requisition", cascade="all, delete-orphan"
    )


class RequisitionItem(Base):
    __tablename__ = "requisition_items"

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity_requested = Column(Integer, nullable=False)
    quantity_approved = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    requisition = relationship("Requisition", back_populates="items")
    item = relationship("Item")


# ── Vendor Uploads (NEW) ─────────────────────────────────────────────────

class VendorUpload(Base):
    """Tracks Excel delivery uploads by vendors."""
    __tablename__ = "vendor_uploads"

    id = Column(Integer, primary_key=True, index=True)
    vendor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    total_rows = Column(Integer, nullable=False, default=0)
    success_rows = Column(Integer, nullable=False, default=0)
    error_rows = Column(Integer, nullable=False, default=0)
    errors_detail = Column(JSON, nullable=True)  # [{row: 3, reason: "item not found"}]
    status = Column(String(20), nullable=False, default="PROCESSING")  # PROCESSING, COMPLETED, FAILED
    uploaded_at = Column(TIMESTAMP, server_default=func.now())

    vendor = relationship("User")
    location = relationship("Location")


# ── Audit Log ─────────────────────────────────────────────────────────────

class AuditLog(Base):
    """Tracks all user actions for audit trail."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    username = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User")
