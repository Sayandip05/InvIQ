"""
Audit service — provides a clean interface for logging user actions.

Used by route handlers to record all significant actions for compliance
and traceability. Failures are logged but never block the main operation.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.infrastructure.database.audit_repo import AuditRepository

logger = logging.getLogger("smart_inventory.service.audit")


class AuditService:
    """Thin wrapper around AuditRepository for easy use in routes."""

    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(
        self,
        username: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Record an audit entry.  Swallows exceptions so the caller's
        main operation is never interrupted by an audit failure.
        """
        try:
            self.repo.create(
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                details=details,
                ip_address=ip_address,
            )
        except Exception as e:
            logger.warning("Audit log failed (non-blocking): %s", e)

    @staticmethod
    def from_db(db: Session) -> "AuditService":
        return AuditService(db)
