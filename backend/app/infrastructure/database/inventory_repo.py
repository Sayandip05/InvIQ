import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import date
from typing import Optional, List

from app.infrastructure.database.models import Location, Item, InventoryTransaction
from app.core.exceptions import DatabaseError, DuplicateError

logger = logging.getLogger("smart_inventory.repo.inventory")


class InventoryRepository:
    """Encapsulates all inventory-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_locations(self) -> List[Location]:
        return self.db.query(Location).all()

    def get_location_by_id(self, location_id: int) -> Optional[Location]:
        return self.db.query(Location).filter(Location.id == location_id).first()

    def get_location_by_name(self, name: str) -> Optional[Location]:
        return self.db.query(Location).filter(Location.name == name).first()

    def create_location(self, **kwargs) -> Location:
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

    def get_all_items(self) -> List[Item]:
        return self.db.query(Item).all()

    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        return self.db.query(Item).filter(Item.id == item_id).first()

    def get_item_by_name(self, name: str) -> Optional[Item]:
        return self.db.query(Item).filter(Item.name == name).first()

    def create_item(self, **kwargs) -> Item:
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

    def get_previous_transaction(
        self, location_id: int, item_id: int, before_date: date
    ) -> Optional[InventoryTransaction]:
        return (
            self.db.query(InventoryTransaction)
            .filter(
                InventoryTransaction.location_id == location_id,
                InventoryTransaction.item_id == item_id,
                InventoryTransaction.date < before_date,
            )
            .order_by(InventoryTransaction.date.desc())
            .first()
        )

    def get_latest_transaction(
        self, location_id: int, item_id: int
    ) -> Optional[InventoryTransaction]:
        return (
            self.db.query(InventoryTransaction)
            .filter(
                InventoryTransaction.location_id == location_id,
                InventoryTransaction.item_id == item_id,
            )
            .order_by(InventoryTransaction.date.desc())
            .first()
        )

    def create_transaction(self, **kwargs) -> InventoryTransaction:
        try:
            tx = InventoryTransaction(**kwargs)
            self.db.add(tx)
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

    def delete_all_transactions(self) -> int:
        try:
            count = self.db.query(InventoryTransaction).delete()
            self.db.commit()
            return count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting transactions: %s", str(e))
            raise DatabaseError(f"Failed to delete transactions: {str(e)}")

    def delete_all_items(self) -> int:
        try:
            count = self.db.query(Item).delete()
            self.db.commit()
            return count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting items: %s", str(e))
            raise DatabaseError(f"Failed to delete items: {str(e)}")

    def delete_all_locations(self) -> int:
        try:
            count = self.db.query(Location).delete()
            self.db.commit()
            return count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting locations: %s", str(e))
            raise DatabaseError(f"Failed to delete locations: {str(e)}")

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
