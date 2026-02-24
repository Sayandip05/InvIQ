from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)
    region = Column(String(100), nullable=False)
    address = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    transactions = relationship("InventoryTransaction", back_populates="location")

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    min_stock = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
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
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    location = relationship("Location", back_populates="transactions")
    item = relationship("Item", back_populates="transactions")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String(100), primary_key=True)
    user_id = Column(String(100), default="admin")
    title = Column(String(200), default="New Conversation")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")


# ─── Stock OUT Requisition System ───

class Requisition(Base):
    __tablename__ = "requisitions"

    id = Column(Integer, primary_key=True, index=True)
    requisition_number = Column(String(50), unique=True, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    requested_by = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    urgency = Column(String(20), nullable=False, default="NORMAL")  # LOW, NORMAL, HIGH, EMERGENCY
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED, CANCELLED
    approved_by = Column(String(100), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    location = relationship("Location")
    items = relationship("RequisitionItem", back_populates="requisition", cascade="all, delete-orphan")


class RequisitionItem(Base):
    __tablename__ = "requisition_items"

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity_requested = Column(Integer, nullable=False)
    quantity_approved = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    requisition = relationship("Requisition", back_populates="items")
    item = relationship("Item")
