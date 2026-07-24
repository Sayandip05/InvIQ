"""
Domain repository interfaces — abstract contracts for the infrastructure layer.

Each concrete repository in infrastructure/database/ implements one of
these Protocols.  Application services depend on these interfaces, not on
the concrete SQLAlchemy implementations, which:

  • Makes unit-testing services trivial — inject a Mock that satisfies
    the Protocol; no real DB session needed.
  • Enforces the dependency-inversion principle: high-level policy
    (application services) does not depend on low-level details (SQLAlchemy).
  • Makes future storage migrations (e.g. to async SQLAlchemy or a different
    ORM) non-breaking — only the concrete repo needs to change.

Usage
─────
    from app.domain.interfaces import IInventoryRepository

    class InventoryService:
        def __init__(self, repo: IInventoryRepository) -> None:
            self._repo = repo

Protocol vs ABC
───────────────
We use typing.Protocol (structural sub-typing) rather than abc.ABC.
This means:
  • Concrete repos do NOT need to inherit from these classes explicitly.
  • Python's type checker (mypy) validates structural conformance at check-time.
  • No runtime overhead; zero changes required to existing concrete repos.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# IInventoryRepository
# ---------------------------------------------------------------------------

@runtime_checkable
class IInventoryRepository(Protocol):
    """
    Read/write access to inventory items and their stock transactions.

    Implemented by: infrastructure.database.inventory_repo.InventoryRepository
    """

    def get_item_by_id(self, item_id: int) -> Optional[Any]:
        """Return a single Item ORM model by primary key, or None."""
        ...

    def get_items_by_location(self, location_id: int) -> List[Any]:
        """Return all Items stocked at the given location."""
        ...

    def get_all_locations(self) -> List[Any]:
        """Return all Location records."""
        ...

    def get_location_by_id(self, location_id: int) -> Optional[Any]:
        """Return a single Location by primary key, or None."""
        ...

    def get_all_items(self) -> List[Any]:
        """Return all Item records."""
        ...

    def create_transaction(self, transaction_data: Dict) -> Any:
        """
        Persist a new inventory transaction and update closing stock.

        Args:
            transaction_data: Dict matching InventoryTransaction fields.

        Returns:
            The newly created InventoryTransaction ORM instance.
        """
        ...

    def get_transactions_for_item(
        self,
        item_id: int,
        location_id: int,
        limit: int = 30,
    ) -> List[Any]:
        """Return recent transactions for an item at a given location."""
        ...


# ---------------------------------------------------------------------------
# IUserRepository
# ---------------------------------------------------------------------------

@runtime_checkable
class IUserRepository(Protocol):
    """
    Read/write access to user accounts.

    Implemented by: infrastructure.database.user_repo.UserRepository
    """

    def get_by_id(self, user_id: int) -> Optional[Any]:
        """Return a User by primary key, or None."""
        ...

    def get_by_username(self, username: str) -> Optional[Any]:
        """Return a User by unique username, or None."""
        ...

    def get_by_email(self, email: str) -> Optional[Any]:
        """Return a User by unique email, or None."""
        ...

    def get_all(self) -> List[Any]:
        """Return all User records."""
        ...

    def create(self, user_data: Dict) -> Any:
        """
        Persist a new user account.

        Args:
            user_data: Dict matching User fields (password must be pre-hashed).

        Returns:
            The newly created User ORM instance.
        """
        ...

    def update(self, user_id: int, updates: Dict) -> Optional[Any]:
        """
        Apply a partial update to an existing user.

        Args:
            user_id: Primary key of the user to update.
            updates: Dict of field name → new value.

        Returns:
            Updated User ORM instance, or None if user not found.
        """
        ...

    def record_login(self, user: Any) -> None:
        """Update last_login_at and reset failed-login counters."""
        ...

    def count(self) -> int:
        """Return total number of user accounts."""
        ...

    def count_filtered(self, **filters: Any) -> int:
        """Return count of users matching keyword filters (e.g. role='admin')."""
        ...


# ---------------------------------------------------------------------------
# IRequisitionRepository
# ---------------------------------------------------------------------------

@runtime_checkable
class IRequisitionRepository(Protocol):
    """
    Read/write access to requisitions and their line items.

    Implemented by: infrastructure.database.requisition_repo.RequisitionRepository
    """

    def get_by_id(self, requisition_id: int) -> Optional[Any]:
        """Return a Requisition by primary key, or None."""
        ...

    def get_all(
        self,
        status: Optional[str] = None,
        location_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Any]:
        """Return requisitions, optionally filtered by status or location."""
        ...

    def create(self, requisition_data: Dict, items: List[Dict]) -> Any:
        """
        Persist a new requisition with its line items atomically.

        Args:
            requisition_data: Dict matching Requisition header fields.
            items:            List of dicts matching RequisitionItem fields.

        Returns:
            The newly created Requisition ORM instance.
        """
        ...

    def approve(self, requisition_id: int, approved_by: str) -> Optional[Any]:
        """
        Transition requisition to APPROVED status.

        Returns:
            Updated Requisition, or None if not found / already processed.
        """
        ...

    def reject(self, requisition_id: int, rejected_by: str, reason: str) -> Optional[Any]:
        """
        Transition requisition to REJECTED status.

        Returns:
            Updated Requisition, or None if not found / already processed.
        """
        ...


# ---------------------------------------------------------------------------
# IAuditRepository
# ---------------------------------------------------------------------------

@runtime_checkable
class IAuditRepository(Protocol):
    """
    Append-only audit trail storage.

    Implemented by: infrastructure.database.audit_repo.AuditRepository
    """

    def log(
        self,
        user_id: Optional[int],
        username: str,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Append an audit event.  Never raises; errors are logged silently."""
        ...

    def get_recent(self, limit: int = 100) -> List[Any]:
        """Return the most recent audit log entries."""
        ...

    def get_by_user(self, username: str, limit: int = 100) -> List[Any]:
        """Return audit entries attributed to a specific username."""
        ...
