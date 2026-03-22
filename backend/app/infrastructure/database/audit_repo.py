"""
Audit log repository — database operations for audit trail.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List, Dict, Any

from app.infrastructure.database.models import AuditLog
from app.core.exceptions import DatabaseError

logger = logging.getLogger("smart_inventory.repo.audit")


class AuditRepository:
    """Encapsulates all audit-log-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        username: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        try:
            log = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return log
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error creating audit log: %s", str(e))
            raise DatabaseError(f"Failed to create audit log: {str(e)}")

    def get_recent(self, limit: int = 50) -> List[AuditLog]:
        try:
            return (
                self.db.query(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error("Database error fetching audit logs: %s", str(e))
            raise DatabaseError(f"Failed to fetch audit logs: {str(e)}")

    def get_by_user(self, username: str, limit: int = 50) -> List[AuditLog]:
        try:
            return (
                self.db.query(AuditLog)
                .filter(AuditLog.username == username)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error("Database error fetching user audit logs: %s", str(e))
            raise DatabaseError(f"Failed to fetch user audit logs: {str(e)}")

    def get_by_resource(
        self, resource_type: str, resource_id: str, limit: int = 50
    ) -> List[AuditLog]:
        try:
            return (
                self.db.query(AuditLog)
                .filter(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id,
                )
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error("Database error fetching resource audit logs: %s", str(e))
            raise DatabaseError(f"Failed to fetch resource audit logs: {str(e)}")
