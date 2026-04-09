"""
Super Admin API — Platform-level organization and user management.

Only accessible by users with role='super_admin'.
These endpoints manage organizations and assign admin roles across the platform.
"""

import logging
import re
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.dependencies import get_db, require_super_admin
from app.core.rate_limiter import limiter
from app.core.exceptions import ValidationError, NotFoundError, DuplicateError
from app.core.security import hash_password
from app.infrastructure.database.models import Organization, User
from app.application.audit_service import AuditService

logger = logging.getLogger("smart_inventory.superadmin")

router = APIRouter(prefix="/superadmin", tags=["Super Admin"])


def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ── Pydantic Schemas ───────────────────────────────────────────────────────

class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")


class UpdateOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    is_active: bool = True


class CreateOrgAdminRequest(BaseModel):
    email: str
    username: str
    password: str = Field(min_length=8)
    full_name: str


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
    }


# ── POST /superadmin/organizations ─────────────────────────────────────────

@router.post("/organizations")
@limiter.limit("10/minute")
def create_organization(
    request: Request,
    body: CreateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Create a new organization."""
    # Check for duplicate slug
    existing = db.query(Organization).filter(Organization.slug == body.slug).first()
    if existing:
        raise DuplicateError(f"Organization with slug '{body.slug}' already exists")

    org = Organization(
        name=body.name,
        slug=body.slug,
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Audit log
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="create_organization",
        resource_type="organization",
        resource_id=str(org.id),
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )

    logger.info("Organization '%s' created by %s", org.name, current_user.username)

    return {
        "success": True,
        "message": f"Organization '{org.name}' created successfully",
        "data": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "is_active": org.is_active,
        },
    }


# ── PUT /superadmin/organizations/{org_id} ─────────────────────────────────

@router.put("/organizations/{org_id}")
@limiter.limit("10/minute")
def update_organization(
    org_id: int,
    request: Request,
    body: UpdateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Update an organization."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization", org_id)

    org.name = body.name
    org.is_active = body.is_active
    db.commit()
    db.refresh(org)

    # Audit log
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="update_organization",
        resource_type="organization",
        resource_id=str(org.id),
        user_id=current_user.id,
        details={"name": body.name, "is_active": body.is_active},
        ip_address=_get_client_ip(request),
    )

    logger.info("Organization '%s' updated by %s", org.name, current_user.username)

    return {
        "success": True,
        "message": f"Organization '{org.name}' updated successfully",
        "data": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "is_active": org.is_active,
        },
    }


# ── DELETE /superadmin/organizations/{org_id} ──────────────────────────────

@router.delete("/organizations/{org_id}")
@limiter.limit("5/minute")
def delete_organization(
    org_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Delete an organization (soft delete by setting is_active=False)."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization", org_id)

    # Check if org has users
    user_count = db.query(User).filter(User.org_id == org_id).count()
    if user_count > 0:
        raise ValidationError(
            f"Cannot delete organization with {user_count} users. "
            "Deactivate it instead or reassign users first."
        )

    org.is_active = False
    db.commit()

    # Audit log
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="delete_organization",
        resource_type="organization",
        resource_id=str(org.id),
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )

    logger.info("Organization '%s' deleted by %s", org.name, current_user.username)

    return {
        "success": True,
        "message": f"Organization '{org.name}' deactivated successfully",
    }


# ── POST /superadmin/organizations/{org_id}/admin ──────────────────────────

@router.post("/organizations/{org_id}/admin")
@limiter.limit("10/minute")
def create_org_admin(
    org_id: int,
    request: Request,
    body: CreateOrgAdminRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Create an admin user for a specific organization."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization", org_id)

    # Check for duplicate username/email
    existing = (
        db.query(User)
        .filter((User.username == body.username) | (User.email == body.email))
        .first()
    )
    if existing:
        raise DuplicateError("User with this username or email already exists")

    user = User(
        org_id=org_id,
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Audit log
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="create_org_admin",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        details={"org_id": org_id, "username": body.username, "role": "admin"},
        ip_address=_get_client_ip(request),
    )

    logger.info(
        "Admin user '%s' created for org '%s' by %s",
        user.username,
        org.name,
        current_user.username,
    )

    return {
        "success": True,
        "message": f"Admin user '{user.username}' created for organization '{org.name}'",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "org_id": org_id,
        },
    }


# ── GET /superadmin/users ──────────────────────────────────────────────────

@router.get("/users")
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """List all users across all organizations."""
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()

    return {
        "success": True,
        "data": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
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
        },
    }
