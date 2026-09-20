import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from datetime import date
from typing import Optional, List, Dict, Any


from app.infrastructure.database.models import Location, Item, InventoryTransaction
from app.core.exceptions import DatabaseError, DuplicateError, ValidationError

logger = logging.getLogger("smart_inventory.repo.inventory")


import time
class InventoryRepository:
    """Encapsulates all inventory-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_locations(self, limit: int = 50, offset: int = 0, org_id: Optional[int] = None) -> List[Location]:
        q = self.db.query(Location)
        if org_id is not None:
            q = q.filter(Location.org_id == org_id)
        return q.offset(offset).limit(limit).all()

    def get_location_by_id(self, location_id: int, org_id: Optional[int] = None) -> Optional[Location]:
        q = self.db.query(Location).filter(Location.id == location_id)
        if org_id is not None:
            q = q.filter(Location.org_id == org_id)
        return q.first()

    def get_location_by_name(self, name: str, org_id: Optional[int] = None) -> Optional[Location]:
        q = self.db.query(Location).filter(Location.name == name)
        if org_id is not None:
            q = q.filter(Location.org_id == org_id)
        return q.first()

    def create_location(self, **kwargs) -> Location:
        if "org_id" not in kwargs or kwargs["org_id"] is None:
            raise ValidationError("Organization ID (org_id) is required to create a location")
        try:
            location = Location(**kwargs)
            self.db.add(location)
            self.db.commit()
            self.db.refresh(location)
            return location
        except IntegrityError:
            self.db.rollback()
            raise DuplicateError("Location already exists")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error creating location: %s", str(e))
            raise DatabaseError(f"Failed to create location: {str(e)}")

    def update_location(self, location: Location, **kwargs) -> Location:
        try:
            for key, val in kwargs.items():
                if hasattr(location, key) and val is not None:
                    setattr(location, key, val)
            self.db.commit()
            self.db.refresh(location)
            return location
        except IntegrityError:
            self.db.rollback()
            raise DuplicateError("A location with this name already exists")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error updating location: %s", str(e))
            raise DatabaseError(f"Failed to update location: {str(e)}")

    def has_location_transactions(self, location_id: int) -> bool:
        """Check if any transaction history exists for this location."""
        return self.db.query(InventoryTransaction).filter(InventoryTransaction.location_id == location_id).first() is not None

    def delete_location(self, location: Location) -> bool:
        try:
            self.db.delete(location)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting location: %s", str(e))
            raise DatabaseError(f"Failed to delete location: {str(e)}")


    def get_all_items(self, limit: int = 50, offset: int = 0, org_id: Optional[int] = None) -> List[Item]:
        q = self.db.query(Item)
        if org_id is not None:
            q = q.filter(Item.org_id == org_id)
        return q.offset(offset).limit(limit).all()

    def get_item_by_id(self, item_id: int, org_id: Optional[int] = None) -> Optional[Item]:
        q = self.db.query(Item).filter(Item.id == item_id)
        if org_id is not None:
            q = q.filter(Item.org_id == org_id)
        return q.first()

    def get_item_by_name(self, name: str, org_id: Optional[int] = None) -> Optional[Item]:
        q = self.db.query(Item).filter(Item.name == name)
        if org_id is not None:
            q = q.filter(Item.org_id == org_id)
        return q.first()

    def get_item_by_barcode(self, barcode: str, org_id: Optional[int] = None) -> Optional[Item]:
        q = self.db.query(Item).filter(Item.barcode == barcode.strip())
        if org_id is not None:
            q = q.filter(Item.org_id == org_id)
        return q.first()





    def create_item(self, **kwargs) -> Item:
        if "org_id" not in kwargs or kwargs["org_id"] is None:
            raise ValidationError("Organization ID (org_id) is required to create an item")
        try:
            item = Item(**kwargs)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except IntegrityError:
            self.db.rollback()
            raise DuplicateError("Item already exists")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error creating item: %s", str(e))
            raise DatabaseError(f"Failed to create item: {str(e)}")

    def update_item(self, item: Item, **kwargs) -> Item:
        try:
            for key, val in kwargs.items():
                if val is not None and hasattr(item, key):
                    setattr(item, key, val)
            self.db.commit()
            self.db.refresh(item)
            return item
        except IntegrityError:
            self.db.rollback()
            raise DuplicateError("Item update caused a duplicate constraint violation")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error updating item: %s", str(e))
            raise DatabaseError(f"Failed to update item: {str(e)}")

    def has_item_transactions(self, item_id: int) -> bool:
        count = self.db.query(InventoryTransaction).filter(
            InventoryTransaction.item_id == item_id
        ).count()
        return count > 0

    def delete_item(self, item: Item) -> bool:
        try:
            self.db.delete(item)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting item: %s", str(e))
            raise DatabaseError(f"Failed to delete item: {str(e)}")


    def acquire_advisory_lock(self, location_id: int, item_id: int) -> None:
        """Acquire a Postgres transaction-scoped advisory lock on (location_id, item_id).

        Prevents race conditions on initial stock creation and concurrent inventory transactions.
        Automatically released when the current database transaction commits or rolls back.
        Safely no-ops when running against non-Postgres engines (e.g. SQLite test runners).

        NOTE: We intentionally avoid Python's built-in hash() here because it is
        randomised per-process (PYTHONHASHSEED).  Two Gunicorn workers would compute
        different lock keys for the same (location_id, item_id) pair, giving zero
        mutual exclusion.  The deterministic formula below is collision-free for all
        item_id values up to 999_999 (well within the domain range).
        """
        try:
            bind = self.db.get_bind()
            if bind and getattr(bind.dialect, "name", "") == "postgresql":
                from sqlalchemy import text
                # Deterministic, cross-process stable key — no PYTHONHASHSEED influence.
                lock_key = (location_id * 1_000_000 + item_id) & 0x7FFFFFFF
                self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
        except Exception as e:
            logger.debug("Advisory lock skipped or unsupported: %s", e)

    def has_later_transactions(self, location_id: int, item_id: int, after_date: date) -> bool:
        """Check if any transaction history exists strictly after after_date for this item/location."""
        return (
            self.db.query(InventoryTransaction)
            .filter(
                InventoryTransaction.location_id == location_id,
                InventoryTransaction.item_id == item_id,
                InventoryTransaction.date > after_date,
            )
            .first()
            is not None
        )

    def get_previous_transaction(
        self, location_id: int, item_id: int, before_date: date, lock: bool = False
    ) -> Optional[InventoryTransaction]:
        """Return the most recent transaction on or before before_date.

        Args:
            lock: If True, acquire a row-level UPDATE lock (SELECT ... FOR UPDATE).
                  Must be used inside an open transaction. Prevents concurrent
                  stock reads from racing against each other.
        """
        q = (
            self.db.query(InventoryTransaction)
            .filter(
                InventoryTransaction.location_id == location_id,
                InventoryTransaction.item_id == item_id,
                InventoryTransaction.date <= before_date,
            )
            .order_by(InventoryTransaction.date.desc(), InventoryTransaction.id.desc())
        )
        if lock:
            q = q.with_for_update()
        return q.first()



    def get_latest_transaction(
        self, location_id: int, item_id: int
    ) -> Optional[InventoryTransaction]:
        return (
            self.db.query(InventoryTransaction)
            .filter(
                InventoryTransaction.location_id == location_id,
                InventoryTransaction.item_id == item_id,
            )
            .order_by(
                InventoryTransaction.date.desc(),
                InventoryTransaction.id.desc(),
            )
            .first()
        )

    def get_latest_stocks_for_location(self, location_id: int) -> Dict[int, int]:
        """
        Single query: returns {item_id: closing_stock} for the latest transaction
        of every item at the given location. Deterministically selects the latest
        record (max transaction ID per item) to handle same-day transactions accurately.
        """
        # Subquery: find the max transaction ID per item at this location
        latest_id_sub = (
            self.db.query(
                InventoryTransaction.item_id,
                func.max(InventoryTransaction.id).label("max_id"),
            )
            .filter(InventoryTransaction.location_id == location_id)
            .group_by(InventoryTransaction.item_id)
            .subquery()
        )

        # Join back to get the closing_stock of that latest transaction
        rows = (
            self.db.query(
                InventoryTransaction.item_id,
                InventoryTransaction.closing_stock,
            )
            .join(
                latest_id_sub,
                InventoryTransaction.id == latest_id_sub.c.max_id,
            )
            .filter(InventoryTransaction.location_id == location_id)
            .all()
        )

        return {row.item_id: row.closing_stock for row in rows}

    def get_available_batches_fefo(self, location_id: int, item_id: int) -> List[Dict[str, Any]]:
        """
        Compute net available stock per batch (received - issued) for a given location and item.
        Returns all batches with net available stock > 0,
        sorted in FEFO order (earliest expiry_date first, null expiries last).
        """
        rows = (
            self.db.query(
                InventoryTransaction.batch_number,
                InventoryTransaction.expiry_date,
                func.sum(InventoryTransaction.received).label("total_received"),
                func.sum(InventoryTransaction.issued).label("total_issued"),
            )
            .filter(
                InventoryTransaction.location_id == location_id,
                InventoryTransaction.item_id == item_id,
                InventoryTransaction.batch_number.isnot(None),
            )
            .group_by(InventoryTransaction.batch_number, InventoryTransaction.expiry_date)
            .all()
        )

        available_batches = []
        for r in rows:
            net_qty = (r.total_received or 0) - (r.total_issued or 0)
            if net_qty > 0:
                available_batches.append({
                    "batch_number": r.batch_number,
                    "expiry_date": r.expiry_date,
                    "available_qty": net_qty,
                })

        # Sort FEFO: earliest expiry first, nulls at the end
        available_batches.sort(key=lambda b: (b["expiry_date"] is None, b["expiry_date"]))
        return available_batches

    def create_transaction(self, flush_only: bool = False, **kwargs) -> InventoryTransaction:

        """
        Create an inventory transaction.

        Args:
            flush_only: If True, flush to DB (get ID) but do NOT commit.
                        The caller is responsible for calling commit().
                        Used by requisition approval for atomic multi-item operations.
        """
        try:
            tx = InventoryTransaction(**kwargs)
            self.db.add(tx)
            if flush_only:
                self.db.flush()  # Stage the write, assign PK, but don't commit
            else:
                self.db.commit()
            self.db.refresh(tx)
            return tx
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error creating transaction: %s", str(e))
            raise DatabaseError(f"Failed to create transaction: {str(e)}")

    def count_transactions(self) -> int:
        return self.db.query(InventoryTransaction).count()

    def count_items(self) -> int:
        return self.db.query(Item).count()

    def count_locations(self) -> int:
        return self.db.query(Location).count()

    def delete_all_transactions(self, org_id: Optional[int] = None) -> int:
        """Delete inventory transactions. If org_id is given, only that org's data is deleted."""
        try:
            q = self.db.query(InventoryTransaction)
            if org_id is not None:
                q = q.filter(
                    InventoryTransaction.location_id.in_(
                        self.db.query(Location.id).filter(Location.org_id == org_id)
                    )
                )
            count = q.delete(synchronize_session=False)
            self.db.commit()
            return count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting transactions: %s", str(e))
            raise DatabaseError(f"Failed to delete transactions: {str(e)}")

    def delete_all_items(self, org_id: Optional[int] = None) -> int:
        """Delete items. If org_id is given, only that org's items are deleted."""
        try:
            q = self.db.query(Item)
            if org_id is not None:
                q = q.filter(Item.org_id == org_id)
            count = q.delete(synchronize_session=False)
            self.db.commit()
            return count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting items: %s", str(e))
            raise DatabaseError(f"Failed to delete items: {str(e)}")

    def delete_all_locations(self, org_id: Optional[int] = None) -> int:
        """Delete locations. If org_id is given, only that org's locations are deleted."""
        try:
            q = self.db.query(Location)
            if org_id is not None:
                q = q.filter(Location.org_id == org_id)
            count = q.delete(synchronize_session=False)
            self.db.commit()
            return count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting locations: %s", str(e))
            raise DatabaseError(f"Failed to delete locations: {str(e)}")

    def get_packaging_by_barcode(self, barcode: str, org_id: Optional[int] = None):
        return None

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

