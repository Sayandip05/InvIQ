import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import func, desc
from datetime import date
from typing import Optional, List

from app.infrastructure.database.models import (
    Requisition,
    RequisitionItem,
    Item,
    Location,
)
from app.core.exceptions import DatabaseError, DuplicateError

logger = logging.getLogger("smart_inventory.repo.requisition")


class RequisitionRepository:
    """Encapsulates all requisition-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self, requisition_id: int, load_items: bool = False, org_id: Optional[int] = None
    ) -> Optional[Requisition]:
        query = self.db.query(Requisition)
        if load_items:
            query = query.options(joinedload(Requisition.items))
        query = query.filter(Requisition.id == requisition_id)
        if org_id is not None:
            query = query.filter(Requisition.org_id == org_id)
        return query.first()

    def get_with_full_details(self, requisition_id: int, org_id: Optional[int] = None) -> Optional[Requisition]:
        query = (
            self.db.query(Requisition)
            .options(
                joinedload(Requisition.location),
                joinedload(Requisition.items).joinedload(RequisitionItem.item),
            )
            .filter(Requisition.id == requisition_id)
        )
        if org_id is not None:
            query = query.join(Location, Requisition.location_id == Location.id).filter(
                Location.org_id == org_id
            )
        return query.first()

    def list_all(
        self,
        status: Optional[str] = None,
        location_id: Optional[int] = None,
        requested_by: Optional[str] = None,
        org_id: Optional[int] = None,
    ) -> List[Requisition]:
        query = self.db.query(Requisition).options(
            joinedload(Requisition.location),
            joinedload(Requisition.items).joinedload(RequisitionItem.item),
        )

        if org_id is not None:
            query = query.join(Location, Requisition.location_id == Location.id).filter(
                Location.org_id == org_id
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

    def get_next_requisition_number(self, target_date: Optional[date] = None) -> str:
        """Generate sequential requisition number: REQ-YYYYMMDD-001, REQ-YYYYMMDD-002, etc.

        Uses max existing sequence for the date to avoid duplicate counts.
        """
        if target_date is None:
            target_date = date.today()

        date_prefix = target_date.strftime("%Y%m%d")
        prefix = f"REQ-{date_prefix}-"

        latest = (
            self.db.query(Requisition.requisition_number)
            .filter(Requisition.requisition_number.like(f"{prefix}%"))
            .order_by(Requisition.requisition_number.desc())
            .first()
        )

        if latest and latest[0]:
            try:
                seq_part = str(latest[0]).split("-")[-1]
                sequence = int(seq_part) + 1
            except (ValueError, IndexError):
                sequence = self.count_by_prefix(prefix) + 1
        else:
            sequence = 1

        return f"{prefix}{sequence:03d}"

    def create(self, **kwargs) -> Requisition:
        try:
            requisition = Requisition(**kwargs)
            self.db.add(requisition)
            self.db.flush()
            return requisition
        except IntegrityError:
            self.db.rollback()
            raise DuplicateError("A requisition with this number already exists")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error creating requisition: %s", str(e))
            raise DatabaseError(f"Failed to create requisition: {str(e)}")

    def add_item(self, **kwargs) -> RequisitionItem:
        try:
            item = RequisitionItem(**kwargs)
            self.db.add(item)
            self.db.flush()
            return item
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error adding requisition item: %s", str(e))
            raise DatabaseError(f"Failed to add requisition item: {str(e)}")

    def get_location(self, location_id: int) -> Optional[Location]:
        return self.db.query(Location).filter(Location.id == location_id).first()

    def get_item(self, item_id: int) -> Optional[Item]:
        return self.db.query(Item).filter(Item.id == item_id).first()

    def count_total(self, org_id: Optional[int] = None) -> int:
        q = self.db.query(Requisition)
        if org_id is not None:
            q = q.join(Location, Requisition.location_id == Location.id).filter(
                Location.org_id == org_id
            )
        return q.count()

    def count_by_status(self, status: str, org_id: Optional[int] = None) -> int:
        q = self.db.query(Requisition).filter(Requisition.status == status)
        if org_id is not None:
            q = q.join(Location, Requisition.location_id == Location.id).filter(
                Location.org_id == org_id
            )
        return q.count()

    def count_approved_today(self, org_id: Optional[int] = None) -> int:
        today = date.today()
        q = self.db.query(Requisition).filter(
            Requisition.status == "APPROVED",
            func.date(Requisition.updated_at) == today,
        )
        if org_id is not None:
            q = q.join(Location, Requisition.location_id == Location.id).filter(
                Location.org_id == org_id
            )
        return q.count()

    def count_emergency_pending(self, org_id: Optional[int] = None) -> int:
        q = self.db.query(Requisition).filter(
            Requisition.status == "PENDING",
            Requisition.urgency == "EMERGENCY",
        )
        if org_id is not None:
            q = q.join(Location, Requisition.location_id == Location.id).filter(
                Location.org_id == org_id
            )
        return q.count()


    def commit(self):
        try:
            self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database commit error: %s", str(e))
            raise DatabaseError(f"Failed to commit transaction: {str(e)}")

    def rollback(self):
        try:
            self.db.rollback()
        except SQLAlchemyError as e:
            logger.error("Database rollback error: %s", str(e))

    def refresh(self, obj):
        try:
            self.db.refresh(obj)
        except SQLAlchemyError as e:
            logger.error("Database refresh error: %s", str(e))
            raise DatabaseError(f"Failed to refresh object: {str(e)}")
