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
    Float,
    LargeBinary,
    Index,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.infrastructure.database.connection import Base

# ── Enum types (enforced at DB driver level) ───────────────────────────────
_UserRoleEnum = Enum(
    "admin", "staff", "vendor",
    name="user_role",
)
_OrgPlanEnum = Enum(
    "single_pharmacy", "multi_pharmacy",
    name="org_plan",
)


# ── Multi-tenancy root ────────────────────────────────────────────────────

class Organization(Base):
    """Multi-tenancy root — every entity belongs to an org."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(_OrgPlanEnum, nullable=False, default="single_pharmacy")
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    gstin = Column(String(50), nullable=True)
    dl_number = Column(String(100), nullable=True)  # Drug License Number
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="organization")
    locations = relationship("Location", back_populates="organization")
    items = relationship("Item", back_populates="organization")


# ── Users ─────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
        Index("ix_users_org_role", "org_id", "role"),
        Index("ix_users_email_active", "email", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(_UserRoleEnum, nullable=False, default="staff", index=True)
    location_ids = Column(JSON, default=list)  # Scoped locations for staff/vendor — default=list avoids shared mutable
    is_active = Column(Boolean, default=True, index=True)
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
    __table_args__ = (
        Index("ix_locations_org_type", "org_id", "type"),
        Index("ix_locations_org_active", "org_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # retail_counter | cold_storage | branch | warehouse
    region = Column(String(100), nullable=False, index=True)
    radius_meters = Column(Integer, default=500)  # Counter delivery / geofence radius
    pincode = Column(String(20), nullable=True)
    phone = Column(String(30), nullable=True)
    address = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="locations")
    transactions = relationship("InventoryTransaction", back_populates="location")



class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_name_category", "name", "category"),
        Index("ix_items_org_category", "org_id", "category"),
        Index("ix_items_barcode_org", "barcode", "org_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    unit = Column(String(50), nullable=False)
    barcode = Column(String(50), nullable=True, index=True)  # EAN-13 = 13 chars; String(50) has safe headroom
    strength = Column(String(50), nullable=True)
    mrp = Column(Float, nullable=False, default=0.0)
    purchase_rate = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Integer, nullable=False, default=2)
    min_stock = Column(Integer, nullable=False, default=10)


    # ── Pharmacy-specific field ───────────────────────────────────────────
    storage_temp = Column(String(20), nullable=False, default="ambient")  # ambient | cold_chain

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="items")
    transactions = relationship("InventoryTransaction", back_populates="item")
    packagings = relationship("ItemPackaging", back_populates="item", cascade="all, delete-orphan")


class ItemPackaging(Base):
    """
    Defines a packaging tier above the base unit (e.g. strip, box, carton, bottle).
    Maps external package barcodes, package multipliers, and custom package pricing.
    """
    __tablename__ = "item_packagings"
    __table_args__ = (
        Index("ix_item_packagings_item", "item_id"),
        Index("ix_item_packagings_barcode_org", "barcode", "org_id"),
        Index("ix_item_packagings_org_unit", "org_id", "unit_name"),
        Index("ix_item_packagings_item_multiplier", "item_id", "multiplier"),
    )

    id                  = Column(Integer, primary_key=True, index=True)
    item_id             = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id              = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    unit_name           = Column(String(50), nullable=False)  # e.g. "strip", "box", "carton", "bottle"
    multiplier          = Column(Integer, nullable=False, default=1)  # number of base units per package (e.g. 10 tabs/strip, 100 tabs/box)
    barcode             = Column(String(50), nullable=True, index=True)  # package-specific EAN/UPC barcode
    mrp                 = Column(Float, nullable=True)  # package retail price (if null, calculated as multiplier * item.mrp)
    purchase_rate       = Column(Float, nullable=True)  # package distributor purchase rate
    is_default_dispense = Column(Boolean, default=False)  # preselected for retail counter sales
    is_default_purchase = Column(Boolean, default=False)  # preselected for vendor receiving
    created_at          = Column(TIMESTAMP, server_default=func.now())
    updated_at          = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    item         = relationship("Item", back_populates="packagings")
    organization = relationship("Organization")



class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        Index("ix_inv_tx_loc_item_date", "location_id", "item_id", "date"),
        Index("ix_inv_tx_item_date", "item_id", "date"),
        Index("ix_inv_tx_closing_date", "closing_stock", "date"),
        Index("ix_inv_tx_expiry_closing", "expiry_date", "closing_stock"),
    )


    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    opening_stock = Column(Integer, nullable=False)
    received = Column(Integer, nullable=False, default=0)
    issued = Column(Integer, nullable=False, default=0)
    closing_stock = Column(Integer, nullable=False)
    notes = Column(Text)
    entered_by = Column(String(100), default="system")

    # ── Batch-level pharmacy fields ──────────────────────────────────────
    batch_number = Column(String(50), nullable=True, index=True)   # e.g. "BT-25-4821"
    expiry_date = Column(Date, nullable=True, index=True)           # expiry of this batch

    # ── Unit of Measure (UOM) context fields ──────────────────────────────
    transacted_unit = Column(String(50), nullable=True)  # e.g. "strip", "box", "tablet"
    transacted_qty  = Column(Integer, nullable=True)     # e.g. 2 (boxes)
    multiplier      = Column(Integer, nullable=True, default=1)  # e.g. 100

    created_at = Column(TIMESTAMP, server_default=func.now())

    location = relationship("Location", back_populates="transactions")
    item = relationship("Item", back_populates="transactions")



# ── Chat ──────────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True)  # UUID4 = 36 chars
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
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    session = relationship("ChatSession", back_populates="messages")


# ── Requisitions ──────────────────────────────────────────────────────────

class Requisition(Base):
    __tablename__ = "requisitions"
    __table_args__ = (
        Index("ix_requisitions_status_urgency", "status", "urgency"),
        Index("ix_requisitions_loc_created", "location_id", "created_at"),
        Index("ix_requisitions_loc_status", "location_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    requisition_number = Column(String(50), unique=True, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    requested_by = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    urgency = Column(String(20), nullable=False, default="NORMAL", index=True)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(TIMESTAMP, nullable=True)
    rejected_at = Column(TIMESTAMP, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    location = relationship("Location")
    items = relationship(
        "RequisitionItem", back_populates="requisition", cascade="all, delete-orphan"
    )


class RequisitionItem(Base):
    __tablename__ = "requisition_items"
    __table_args__ = (
        Index("ix_req_items_req_item", "requisition_id", "item_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    quantity_requested = Column(Integer, nullable=False)
    quantity_approved = Column(Integer, nullable=True)

    # ── Unit of Measure (UOM) fields ──────────────────────────────────────
    packaging_unit          = Column(String(50), nullable=True)  # e.g. "strip", "box", "tablet"
    multiplier              = Column(Integer, nullable=False, default=1)  # base units per package
    base_quantity_requested = Column(Integer, nullable=True)  # total base units requested
    base_quantity_approved  = Column(Integer, nullable=True)  # total base units approved

    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    requisition = relationship("Requisition", back_populates="items")
    item = relationship("Item")


# ── Vendor Uploads ────────────────────────────────────────────────────────

class VendorUpload(Base):
    """Tracks Excel delivery uploads by vendors."""
    __tablename__ = "vendor_uploads"

    id = Column(Integer, primary_key=True, index=True)
    vendor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    total_rows = Column(Integer, nullable=False, default=0)
    success_rows = Column(Integer, nullable=False, default=0)
    error_rows = Column(Integer, nullable=False, default=0)
    errors_detail = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="PROCESSING", index=True)
    uploaded_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    vendor = relationship("User")
    location = relationship("Location")
    invoice = relationship("VendorInvoice", back_populates="vendor_upload", uselist=False)


# ── Vendor Invoices ───────────────────────────────────────────────────────

class VendorInvoice(Base):
    """
    Formal delivery invoices auto-generated upon processing vendor Excel manifests.
    Stores line items, financial totals, and links to Azure Blob Storage / DB PDF bytes.
    """
    __tablename__ = "vendor_invoices"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    vendor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vendor_upload_id = Column(Integer, ForeignKey("vendor_uploads.id"), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_date = Column(Date, nullable=False, index=True)
    line_items = Column(JSON, nullable=False)
    subtotal = Column(Float, nullable=False, default=0.0)
    tax_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default="ISSUED", index=True)
    pdf_path = Column(String(500), nullable=True)
    pdf_url = Column(Text, nullable=True)  # Azure blob URLs can exceed 1000 chars
    pdf_content = Column(LargeBinary, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    vendor = relationship("User")
    vendor_upload = relationship("VendorUpload", back_populates="invoice")
    organization = relationship("Organization")


# ── Audit Log ─────────────────────────────────────────────────────────────

class AuditLog(Base):
    """Tracks all user actions for audit trail."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_org_created", "org_id", "created_at"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
    )


    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    user = relationship("User")


# ── Data Import ───────────────────────────────────────────────────────────

class DataImportJob(Base):
    __tablename__ = "data_import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    target_entity = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)

    total_rows = Column(Integer, nullable=True)
    success_rows = Column(Integer, nullable=False, default=0)
    quarantined_rows = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    mapping_result = Column(JSON, nullable=True)
    mapping_cache_hit = Column(Boolean, default=False)
    file_content = Column(LargeBinary, nullable=True)
    file_blob_path = Column(String(500), nullable=True)
    file_blob_url = Column(Text, nullable=True)
    is_background = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    uploaded_by = relationship("User")
    quarantine_rows = relationship(
        "ImportQuarantineRow",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class ImportQuarantineRow(Base):
    __tablename__ = "import_quarantine_rows"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("data_import_jobs.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False)
    reason = Column(String(30), nullable=False)
    field_name = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    job = relationship("DataImportJob", back_populates="quarantine_rows")


# ── Billing Sessions ──────────────────────────────────────────────────────

class BillingSession(Base):
    """
    Groups barcode scans into a single customer cart at the pharmacy counter.

    Lifecycle: OPEN → CLOSED (on checkout) | CANCELLED (on void).

    The `items` JSON column stores a point-in-time snapshot of every line sold
    so that monthly financial reports remain accurate even if item MRP changes
    after the sale.
    """
    __tablename__ = "billing_sessions"
    __table_args__ = (
        Index("ix_billing_sessions_org_status", "org_id", "status"),
        Index("ix_billing_sessions_org_month", "org_id", "month_key"),
        Index("ix_billing_sessions_location_opened", "location_id", "opened_at"),
        Index("ix_billing_sessions_cashier_opened", "cashier_id", "opened_at"),
    )

    id             = Column(Integer, primary_key=True, index=True)
    org_id         = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    location_id    = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    cashier_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # OPEN | CLOSED | CANCELLED
    status         = Column(String(20), nullable=False, default="OPEN", index=True)

    # Snapshot of items sold — list of dicts:
    # [{ item_id, item_name, barcode, mrp, qty, purchase_rate,
    #    batch_number, transaction_id, line_total }, ...]
    items          = Column(JSON, nullable=False, default=list)

    # Financial breakdown — populated at checkout
    gross_total      = Column(Float, nullable=True)       # Σ (qty × mrp)
    discount_model   = Column(String(20), nullable=True)  # flat | tiered | none
    discount_pct     = Column(Float, nullable=True, default=0.0)
    discount_amount  = Column(Float, nullable=True, default=0.0)
    net_total        = Column(Float, nullable=True)       # gross_total - discount_amount
    purchase_cost    = Column(Float, nullable=True)       # Σ (qty × purchase_rate) — for profit calc

    # Timestamps
    opened_at      = Column(TIMESTAMP, server_default=func.now(), nullable=False, index=True)
    closed_at      = Column(TIMESTAMP, nullable=True)

    # "2026-08" — pre-computed for fast monthly aggregation queries
    month_key      = Column(String(7), nullable=True, index=True)

    # Relationships
    organization   = relationship("Organization")
    location       = relationship("Location")
    cashier        = relationship("User")
