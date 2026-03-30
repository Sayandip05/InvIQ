"""
Super Admin API — Platform-level organization and user management.

Only accessible by users with role='super_admin'.
These endpoints manage organizations and assign admin roles across the platform.
"""

import logging
import re
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_super_admin
from app.core.rate_limiter import limiter
from app.core.exceptions import ValidationError, NotFoundError
from app.core.security import hash_password
from app.infrastructure.database.models import Organization, User
from app.application.audit_service import AuditService

logger = logging.getLogger("smart_inventory.superadmin")

router = APIRouter(prefix="/superadmin", tags=["Super Admin"])


def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ── GET /superadmin/organizations ──────────────────────────────────────────

@router.get("/organizations")
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """List all organizations on the platform."""
    orgs = db.query(Organization).order_by(Organization.created_at.desc()).all()
    return {
        "success": True,
        "data": [
            {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "is_active": org.is_active,
                "user_count": db.query(User).filter(User.org_id == org.id).count(),
                "created_at": str(org.created_at) if org.created_at else None,
            }
            for org in orgs
        ],
        "total": len(orgs),
    }


# ── POST /superadmin/organizations ─────────────────────────────────────────

@router.post("/organizations")
@limiter.limit("10/minute")
def create_organization(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Create a new organization."""
    data = request._json if hasattr(request, '_json') else {}
    # We need to get the body differently in FastAPI
    import json
    body = json.loads(request._body.decode()) if hasattr(request, '_body') else {}

    name = body.get("name", "").strip()
    if not name or len(name) < 2:
        raise ValidationError("Organization name must be at least 2 characters")

    # Generate slug from name
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # Check uniqueness
    existing = db.query(Organization).filter(
        (Organization.name == name) | (Organization.slug == slug)
    ).first()
    if existing:
        raise ValidationError(f"Organization '{name}' already exists")

    org = Organization(name=name, slug=slug)
    db.add(org)
    db.commit()
    db.refresh(org)

    # Audit
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="CREATE_ORGANIZATION",
        resource_type="organization",
        resource_id=str(org.id),
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )

    logger.info("Organization '%s' created by %s", name, current_user.username)

    return {
        "success": True,
        "message": f"Organization '{name}' created",
        "data": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "is_active": True,
        },
    }


# ── GET /superadmin/users ──────────────────────────────────────────────────

@router.get("/users")
def list_all_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """List all users across all organizations."""
    if limit > 100:
        limit = 100

    query = db.query(User).order_by(User.created_at.desc())
    total = query.count()
    users = query.offset(skip).limit(limit).all()

    return {
        "success": True,
        "data": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role,
                "org_id": u.org_id,
                "is_active": u.is_active,
                "created_at": str(u.created_at) if u.created_at else None,
            }
            for u in users
        ],
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total,
        },
    }


# ── POST /superadmin/assign-role ───────────────────────────────────────────

@router.post("/assign-role")
@limiter.limit("10/minute")
def assign_admin_to_org(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Assign admin role to a user and associate them with an organization."""
    import json
    body = json.loads(request._body.decode()) if hasattr(request, '_body') else {}

    user_id = body.get("user_id")
    org_id = body.get("org_id")
    role = body.get("role", "admin")

    if not user_id or not org_id:
        raise ValidationError("user_id and org_id are required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User", user_id)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization", org_id)

    user.role = role
    user.org_id = org_id
    db.commit()

    # Audit
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="ASSIGN_ROLE",
        resource_type="user",
        resource_id=str(user.id),
        details={"role": role, "org_id": org_id},
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )

    logger.info(
        "User %s assigned role '%s' in org %s by %s",
        user.username, role, org.name, current_user.username,
    )

    return {
        "success": True,
        "message": f"User {user.username} assigned role '{role}' in {org.name}",
    }


# ── PUT /superadmin/org/{id}/deactivate ────────────────────────────────────

@router.put("/org/{org_id}/deactivate")
@limiter.limit("5/minute")
def deactivate_organization(
    org_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Deactivate an entire organization and all its users."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization", org_id)

    org.is_active = False

    # Deactivate all users in this org
    deactivated_count = (
        db.query(User)
        .filter(User.org_id == org_id)
        .update({"is_active": False})
    )
    db.commit()

    # Audit
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="DEACTIVATE_ORGANIZATION",
        resource_type="organization",
        resource_id=str(org_id),
        details={"users_deactivated": deactivated_count},
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )

    logger.info(
        "Organization '%s' deactivated by %s (%d users affected)",
        org.name, current_user.username, deactivated_count,
    )

    return {
        "success": True,
        "message": f"Organization '{org.name}' deactivated ({deactivated_count} users affected)",
    }
