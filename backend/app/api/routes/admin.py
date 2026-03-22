"""
Admin Dashboard API — Super Admin endpoints for platform management.

Provides overview stats, user management summaries, and audit trail
access for the platform owner's dashboard.
"""

import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, require_admin
from app.infrastructure.database.models import User, AuditLog
from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.database.audit_repo import AuditRepository

logger = logging.getLogger("smart_inventory.admin")

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


# ── GET /admin/overview ────────────────────────────────────────────────────

@router.get("/overview", response_model=dict)
def get_platform_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Super Admin overview — quick stats for the entire platform.
    Shows total users, active/inactive counts, role breakdown, recent activity.
    """
    user_repo = UserRepository(db)

    total_users = user_repo.count()
    active_users = user_repo.count_filtered(is_active=True)
    inactive_users = user_repo.count_filtered(is_active=False)

    # Role breakdown
    role_counts = {}
    for role in ["admin", "manager", "staff", "viewer"]:
        role_counts[role] = user_repo.count_filtered(role=role)

    # Recent signups (last 7 days)
    recent_users = user_repo.get_all_filtered(limit=5)
    recent_signups = [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in recent_users
    ]

    # Recent audit events
    audit_repo = AuditRepository(db)
    recent_events = audit_repo.get_recent(limit=10)
    recent_activity = [
        {
            "action": e.action,
            "username": e.username,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "created_at": str(e.created_at) if e.created_at else None,
            "ip_address": e.ip_address,
        }
        for e in recent_events
    ]

    return {
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users,
                "by_role": role_counts,
            },
            "recent_signups": recent_signups,
            "recent_activity": recent_activity,
        },
    }


# ── GET /admin/audit-logs ─────────────────────────────────────────────────

@router.get("/audit-logs", response_model=dict)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    username: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    View audit trail — filterable by user, action type, or resource.
    This is the core compliance tool for the super admin.
    """
    audit_repo = AuditRepository(db)

    if username:
        logs = audit_repo.get_by_user(username, limit=limit)
    else:
        logs = audit_repo.get_recent(limit=limit)

    # Apply additional filters in-memory (small dataset)
    if action:
        logs = [l for l in logs if l.action == action]
    if resource_type:
        logs = [l for l in logs if l.resource_type == resource_type]

    return {
        "success": True,
        "data": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": str(log.created_at) if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }


# ── GET /admin/users/summary ──────────────────────────────────────────────

@router.get("/users/summary", response_model=dict)
def get_users_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Detailed user summary for the super admin user management section.
    """
    user_repo = UserRepository(db)
    all_users = user_repo.get_all()

    users_data = []
    for u in all_users:
        users_data.append({
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "login_attempts": u.login_attempts or 0,
            "locked_until": str(u.locked_until) if u.locked_until else None,
            "last_login_at": str(u.last_login_at) if u.last_login_at else None,
            "created_at": str(u.created_at) if u.created_at else None,
            "updated_at": str(u.updated_at) if u.updated_at else None,
        })

    # Identify concerns
    locked_users = [u for u in users_data if u["locked_until"] is not None]
    never_logged_in = [u for u in users_data if u["last_login_at"] is None and u["role"] != "admin"]

    return {
        "success": True,
        "data": {
            "all_users": users_data,
            "total": len(users_data),
            "alerts": {
                "locked_accounts": locked_users,
                "never_logged_in": never_logged_in,
            },
        },
    }
