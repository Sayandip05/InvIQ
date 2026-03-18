"""
Requisition repository — data access layer.

All raw database queries for requisitions and requisition items live here.
"""

import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from datetime import date
from typing import Optional, List

from app.database.models import Requisition, RequisitionItem, Item, Location

logger = logging.getLogger("smart_inventory.repo.requisition")


class RequisitionRepository:
    """Encapsulates all requisition-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self, requisition_id: int, load_items: bool = False
    ) -> Optional[Requisition]:
        query = self.db.query(Requisition)
        if load_items:
            query = query.options(joinedload(Requisition.items))
        return query.filter(Requisition.id == requisition_id).first()

    def get_with_full_details(self, requisition_id: int) -> Optional[Requisition]:
        return (
            self.db.query(Requisition)
            .options(
                joinedload(Requisition.location),
                joinedload(Requisition.items).joinedload(RequisitionItem.item),
            )
            .filter(Requisition.id == requisition_id)
            .first()
        )

    def list_all(
        self,
        status: Optional[str] = None,
        location_id: Optional[int] = None,
        requested_by: Optional[str] = None,
    ) -> List[Requisition]:
        query = self.db.query(Requisition).options(
            joinedload(Requisition.location),
            joinedload(Requisition.items).joinedload(RequisitionItem.item),
        )

        if status:
            query = query.filter(Requisition.status == status.upper())
        if location_id:
            query = query.filter(Requisition.location_id == location_id)
        if requested_by:
            query = query.filter(Requisition.requested_by == requested_by)

        return query.order_by(desc(Requisition.created_at)).all()

    def count_by_prefix(self, prefix: str) -> int:
        return (
            self.db.query(Requisition)
            .filter(Requisition.requisition_number.like(f"{prefix}%"))
            .count()
        )

    def create(self, **kwargs) -> Requisition:
        requisition = Requisition(**kwargs)
        self.db.add(requisition)
        self.db.flush()
        return requisition

    def add_item(self, **kwargs) -> RequisitionItem:
        item = RequisitionItem(**kwargs)
        self.db.add(item)
        return item

    def get_location(self, location_id: int) -> Optional[Location]:
        return self.db.query(Location).filter(Location.id == location_id).first()

    def get_item(self, item_id: int) -> Optional[Item]:
        return self.db.query(Item).filter(Item.id == item_id).first()

    # ── Stats queries ──

    def count_total(self) -> int:
        return self.db.query(Requisition).count()

    def count_by_status(self, status: str) -> int:
        return self.db.query(Requisition).filter(Requisition.status == status).count()

    def count_approved_today(self) -> int:
        today = date.today()
        return (
            self.db.query(Requisition)
            .filter(
                Requisition.status == "APPROVED",
                func.date(Requisition.updated_at) == today,
            )
            .count()
        )

    def count_emergency_pending(self) -> int:
        return (
            self.db.query(Requisition)
            .filter(
                Requisition.status == "PENDING",
                Requisition.urgency == "EMERGENCY",
            )
            .count()
        )

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def refresh(self, obj):
        self.db.refresh(obj)
