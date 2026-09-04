import logging
import os
import time
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional



from app.core.dependencies import (
    get_user_repo,
    get_current_user,
    require_admin,
    get_db_session,
)
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.core.security import (
    authenticate_user,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    hash_password,
    mask_email,
)
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    DuplicateError,
)

from app.infrastructure.database.user_repo import UserRepository
from app.infrastructure.database.models import User, Location
from app.application.audit_service import AuditService
from app.application.notification_service import NotificationService
from app.api.schemas.auth_schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfileUpdate,

    AdminPasswordReset,
    LoginRequest,
    Token,
    RefreshTokenRequest,
    PasswordChangeRequest,
    RoleUpdate,
    VerifyEmailRequest,
    PasswordResetConfirmRequest,
    GoogleAuthRequest,
)


import secrets
import hashlib
import jwt
from app.infrastructure.email import smtp_client

logger = logging.getLogger("smart_inventory.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Constants ──────────────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOCKOUT_DURATION_MINUTES = settings.LOCKOUT_DURATION_MINUTES


# ── Email & Token Helpers ─────────────────────────────────────────────────


def _generate_verification_token(user_id: int, email: str) -> str:
    """Generate a signed verification token for email verification."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "email_verification",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _generate_password_reset_token(user_id: int, email: str) -> str:
    """Generate a signed, single-use token for password reset."""
    import uuid
    from app.infrastructure.cache.token_blacklist import register_reset_jti
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "password_reset",
        "jti": jti,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    register_reset_jti(jti, ttl_seconds=3600)
    return token


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send email via SMTP infrastructure client. Returns True if successful."""
    return smtp_client.send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
    )


def _send_verification_email(user: User, request: Request) -> bool:
    """Send email verification link to user."""
    token = _generate_verification_token(user.id, user.email)
    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Verify your email</h2>
            <p>Click the button below to verify your email and activate your account:</p>
            <a href="{verify_link}" style="background: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 16px 0;">
                Verify Email
            </a>
            <p style="color: #666; font-size: 14px;">This link expires in 24 hours.</p>
            <p style="color: #999; font-size: 12px;">If you didn't create this account, please ignore this email.</p>
        </body>
    </html>
    """
    return _send_email(user.email, "Verify your email - InvIQ", html)


def _send_password_reset_email(user: User) -> bool:
    """Send password reset link to user."""
    token = _generate_password_reset_token(user.id, user.email)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Reset your password</h2>
            <p>Click the button below to reset your password:</p>
            <a href="{reset_link}" style="background: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 16px 0;">
                Reset Password
            </a>
            <p style="color: #666; font-size: 14px;">This link expires in 1 hour.</p>
            <p style="color: #999; font-size: 12px;">If you didn't request a password reset, please ignore this email or contact support.</p>
        </body>
    </html>
    """
    return _send_email(user.email, "Reset your password - InvIQ", html)


# ── Helpers ────────────────────────────────────────────────────────────────


def _user_dict(user: User) -> dict:
    """Standard user data payload reused across endpoints."""
    org_name = None
    if user.organization:
        org_name = user.organization.name
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "org_id": user.org_id,
        "organization_name": org_name,
        "location_ids": user.location_ids or [],
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "last_login_at": str(user.last_login_at) if user.last_login_at else None,
    }


def _get_client_ip(request: Request) -> str:
    """Extract client IP for audit logging."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── POST /register ─────────────────────────────────────────────────────────


@router.post("/register", response_model=dict)
@limiter.limit("3/minute")
def register(
    request_body: UserCreate,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    role = request_body.role or "staff"
    if role not in ["admin", "staff", "vendor"]:
        raise ValidationError(
            f"Invalid role: {role}. Must be admin, staff, or vendor"
        )

    # Allocate new staff / vendor strictly to the current admin's pharmacy organization
    target_org_id = current_user.org_id

    # Validate location_ids against the target organization
    loc_ids = request_body.location_ids or []
    if loc_ids:
        if target_org_id is None:
            raise AuthorizationError("User is not assigned to an organization")
        valid_locs = db.db.query(Location.id).filter(
            Location.id.in_(loc_ids),
            Location.org_id == target_org_id,
        ).all()
        valid_set = {loc[0] for loc in valid_locs}
        invalid_ids = [lid for lid in loc_ids if lid not in valid_set]
        if invalid_ids:
            raise ValidationError(f"Invalid location ID(s): {invalid_ids}. Locations must belong to your organization.")

    user = db.create(
        email=request_body.email,
        username=request_body.username,
        password=request_body.password,
        full_name=request_body.full_name,
        role=request_body.role,
        org_id=target_org_id,
        location_ids=loc_ids,
    )

    # Generate secure activation / password-set token link (no plaintext password in email)
    activation_token = _generate_password_reset_token(user.id, user.email)
    activation_link = f"{settings.FRONTEND_URL}/reset-password?token={activation_token}"

    email_sent = NotificationService.send_welcome_email(
        to_email=user.email,
        username=user.username,
        role=user.role,
        full_name=user.full_name,
        activation_link=activation_link,
    )

    if user.role == "admin":
        NotificationService.send_admin_congratulations_email(
            to_email=user.email,
            username=user.username,
            full_name=user.full_name,
        )

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="USER_CREATED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        org_id=target_org_id,
        details={
            "new_user": user.username,
            "role": user.role,
            "email_sent": email_sent,
        },
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": f"User {user.username} created successfully"
        + (" (welcome email sent)" if email_sent else " (email not sent)"),
        "data": _user_dict(user),
    }


# ── POST /signup ───────────────────────────────────────────────────────────


@router.post("/signup", response_model=dict)
@limiter.limit("5/minute")
def signup(
    request_body: UserCreate,
    request: Request,
    db: Session = Depends(get_user_repo),
):
    """
    Public self-registration endpoint for new users.
    Creates a new user account as Pharmacy Owner / Store Admin.
    """
    if db.get_by_email(request_body.email):
        raise DuplicateError("A user with this email already exists")
    if db.get_by_username(request_body.username):
        raise DuplicateError("A user with this username already exists")

    if request_body.role in ["staff", "vendor"]:
        raise ValidationError(
            "Staff and vendor accounts must be invited by an organization administrator. "
            "Public registration is only available for pharmacy owners/administrators."
        )

    role = "admin"

    org_id = None
    org_name = None
    default_location_id = None
    if role == "admin":
        from app.infrastructure.database.models import Organization, Location
        base_slug = request_body.username.lower().replace(" ", "-").replace(".", "-")
        slug = base_slug
        counter = 1
        while db.db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org_name = f"{request_body.full_name or request_body.username}'s Pharmacy & Medical Store"
        new_org = Organization(name=org_name, slug=slug, is_active=True)
        db.db.add(new_org)
        db.db.commit()
        db.db.refresh(new_org)
        org_id = new_org.id

        # Create initial default counter location
        default_location = Location(
            org_id=new_org.id,
            name=f"{request_body.full_name or request_body.username} - Main Counter",
            type="retail_counter",
            region="Default Region",
            address="Main Store Location",
        )
        db.db.add(default_location)
        db.db.commit()
        db.db.refresh(default_location)
        default_location_id = default_location.id

    user = db.create(
        email=request_body.email,
        username=request_body.username,
        password=request_body.password,
        full_name=request_body.full_name,
        role=role,
        org_id=org_id,
        location_ids=[default_location_id] if default_location_id else (request_body.location_ids or []),
    )


    if user.role == "admin":
        try:
            NotificationService.send_admin_congratulations_email(
                to_email=user.email,
                username=user.username,
                full_name=user.full_name,
                organization_name=org_name,
            )
        except Exception as mail_err:
            logger.warning("Could not send welcome email on signup: %s", mail_err)

        # Asynchronously index onboarding context into Vector Memory
        if user.org_id:
            try:
                from app.workers.tasks import sync_onboarding_context_task
                sync_onboarding_context_task.delay(
                    org_id=user.org_id,
                    user_id=user.id,
                    full_name=user.full_name or user.username,
                    pharmacy_name=org_name,
                    primary_counter="Main Market Counter",
                    plan_type="single_pharmacy",
                    extra_settings={"primary_counter_name": "Main Market Counter"},
                )
            except Exception as vec_err:
                logger.warning("Could not queue vector memory sync on signup: %s", vec_err)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=user.username,
        action="USER_SELF_REGISTERED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        org_id=org_id,
        details={
            "username": user.username,
            "role": user.role,
        },
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": "Account created successfully. You can now log in.",
        "data": _user_dict(user),
    }


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set secure, HttpOnly, SameSite cookies for robust browser authentication."""
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear HttpOnly authentication cookies on logout."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


# ── POST /login ────────────────────────────────────────────────────────────



@router.post("/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(
    request_body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_user_repo),
):

    # Strictly lookup ONLY by email address (case-insensitive)
    login_email = str(request_body.email).strip().lower()
    user = db.get_by_email(login_email)

    # NOTE: we do NOT raise early if user is None — that would leak email
    # existence via timing. authenticate_user() runs a dummy hash in that case.


    # Check account lockout (only if user exists)
    if user and user.locked_until:
        now = datetime.now(timezone.utc)
        if now < user.locked_until:
            remaining = int((user.locked_until - now).total_seconds() // 60) + 1
            raise AuthenticationError(
                f"Account is locked. Try again in {remaining} minutes."
            )
        else:
            # Lock period expired, reset
            db.reset_login_attempts(user)

    # ── Verify password (timing-safe via authenticate_user) ─────────────
    if not authenticate_user(user, request_body.password):
        if user is not None:
            db.increment_login_attempts(user)
            attempts_left = MAX_LOGIN_ATTEMPTS - (user.login_attempts or 0)

            if attempts_left <= 0:
                # Lock the account
                lock_until = datetime.now(timezone.utc) + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )
                db.lock_user(user, lock_until)

                audit = AuditService(db.db)
                audit.log(
                    username=user.username,
                    action="ACCOUNT_LOCKED",
                    resource_type="user",
                    resource_id=str(user.id),
                    user_id=user.id,
                    org_id=user.org_id,
                    details={"reason": "max_login_attempts_exceeded"},
                    ip_address=_get_client_ip(request),
                )

                raise AuthenticationError(
                    f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes due to too many failed attempts."
                )

        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("User account is disabled")


    # Successful login — record it and reset attempts
    db.record_login(user)

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "org_id": user.org_id,
        }
    )
    refresh_token = create_refresh_token({"sub": str(user.id), "username": user.username})

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=user.username,
        action="LOGIN_SUCCESS",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        org_id=user.org_id,
        ip_address=_get_client_ip(request),
    )

    json_resp = JSONResponse(
        content={
            "success": True,
            "message": "Login successful",
            "data": {
                "token_type": "bearer",
                "user": _user_dict(user),
            },
        }
    )
    _set_auth_cookies(json_resp, access_token, refresh_token)
    return json_resp


# ── POST /logout ───────────────────────────────────────────────────────────


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Blacklist the current access token and clear authentication cookies."""
    from app.infrastructure.cache.token_blacklist import (
        blacklist_token,
        blacklist_refresh_token,
    )

    # Extract the access token from the Authorization header or cookie
    access_token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
    elif request.cookies.get("access_token"):
        access_token = request.cookies.get("access_token")

    if access_token:
        blacklist_token(access_token)

    # Extract and blacklist the refresh token from cookie or payload
    refresh_token_str = request.cookies.get("refresh_token")
    if refresh_token_str:
        blacklist_refresh_token(refresh_token_str)

    # Audit log — reuse the injected db session, no extra connection
    try:
        audit = AuditService(db)
        audit.log(
            username=current_user.username,
            action="LOGOUT",
            resource_type="user",
            resource_id=str(current_user.id),
            user_id=current_user.id,
            org_id=current_user.org_id,
            ip_address=_get_client_ip(request),
        )
    except Exception:
        pass

    json_resp = JSONResponse(content={"success": True, "message": "Logged out successfully"})
    _clear_auth_cookies(json_resp)
    return json_resp


# ── POST /refresh ──────────────────────────────────────────────────────────


@router.post("/refresh")
@limiter.limit("10/minute")
def refresh_token(
    request: Request,
    response: Response,
    body_data: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_user_repo),
):

    """
    Refresh access token. Implements token rotation:
    the old refresh token is blacklisted after use (one-time use only).
    """
    from app.infrastructure.cache.token_blacklist import (
        blacklist_refresh_token as bl_refresh,
        is_token_blacklisted,
    )

    refresh_token_str = (body_data.refresh_token if body_data and body_data.refresh_token else None) or request.cookies.get("refresh_token")

    if not refresh_token_str:
        raise AuthenticationError("refresh_token is required")

    # Reject if the refresh token was already used (rotation replay attack)
    if is_token_blacklisted(refresh_token_str):
        raise AuthenticationError("Refresh token has already been used or revoked")

    payload = verify_refresh_token(refresh_token_str)
    user_id = payload.get("sub")

    user = db.get_by_id(user_id)
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    # ── Token rotation: blacklist the old refresh token ────────────────
    bl_refresh(refresh_token_str)

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "org_id": user.org_id,
        }
    )
    new_refresh_token = create_refresh_token(
        {"sub": str(user.id), "username": user.username}
    )

    json_resp = JSONResponse(
        content={
            "success": True,
            "message": "Tokens refreshed (old refresh token revoked)",
            "data": {
                "token_type": "bearer",
            },
        }
    )
    _set_auth_cookies(json_resp, access_token, new_refresh_token)
    return json_resp




# ── GET /me ────────────────────────────────────────────────────────────────


@router.get("/me", response_model=dict)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": _user_dict(current_user),
    }


# ── PATCH /me ──────────────────────────────────────────────────────────────


@router.patch("/me", response_model=dict)
def update_my_profile(
    request_body: UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(get_current_user),
):
    changes = {}
    if request_body.email is not None:
        # Check for duplicate email
        existing = db.get_by_email(str(request_body.email))
        if existing and existing.id != current_user.id:
            raise ValidationError("Email already in use by another account")
        current_user.email = str(request_body.email)
        changes["email"] = str(request_body.email)

    if request_body.username is not None and request_body.username.strip():
        new_username = request_body.username.strip().lower()
        existing = db.get_by_username(new_username)
        if existing and existing.id != current_user.id:
            raise ValidationError("Username already taken")
        current_user.username = new_username
        changes["username"] = new_username

    if request_body.full_name is not None:
        current_user.full_name = request_body.full_name.strip() if request_body.full_name else None
        changes["full_name"] = current_user.full_name

    if not changes:
        raise ValidationError("No fields provided to update")

    db.update(current_user)

    # If full name changed, update vector memory asynchronously
    if "full_name" in changes and current_user.org_id:
        try:
            from app.workers.tasks import sync_onboarding_context_task
            from app.infrastructure.database.models import Organization
            org = db.db.query(Organization).filter(Organization.id == current_user.org_id).first()
            if org:
                primary_counter = (org.settings or {}).get("primary_counter_name", "Main Market Counter")
                plan_type = (org.settings or {}).get("plan_type", org.plan or "single_pharmacy")
                sync_onboarding_context_task.delay(
                    org_id=org.id,
                    user_id=current_user.id,
                    full_name=current_user.full_name or current_user.username,
                    pharmacy_name=org.name,
                    primary_counter=primary_counter,
                    plan_type=plan_type,
                    extra_settings=org.settings or {},
                )
        except Exception as exc:
            logger.warning("Could not sync vector memory on profile update: %s", exc)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="PROFILE_UPDATED",
        resource_type="user",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        org_id=current_user.org_id,
        details=changes,
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": _user_dict(current_user),
    }


# ── POST /change-password ─────────────────────────────────────────────────


@router.post("/change-password", response_model=dict)
def change_password(
    request_body: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(request_body.current_password, current_user.hashed_password):
        raise AuthenticationError("Current password is incorrect")

    current_user.hashed_password = hash_password(request_body.new_password)
    db.update(current_user)

    # Invalidate existing sessions issued before this password change
    try:
        from app.infrastructure.cache.redis_client import get_redis, is_redis_available
        r = get_redis()
        if r and is_redis_available():
            r.setex(f"user_pw_changed:{current_user.id}", 3600 * 24, str(int(time.time())))
    except Exception as e:
        logger.error("Failed to set user_pw_changed in Redis for user %s: %s", current_user.id, str(e))

    # Blacklist caller's current access/refresh tokens to require fresh login
    try:
        from app.infrastructure.cache.token_blacklist import (
            blacklist_token,
            blacklist_refresh_token,
        )
        access_token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header[7:]
        elif request.cookies.get("access_token"):
            access_token = request.cookies.get("access_token")

        if access_token:
            blacklist_token(access_token)

        refresh_token_str = request.cookies.get("refresh_token")
        if refresh_token_str:
            blacklist_refresh_token(refresh_token_str)
    except Exception as e:
        logger.error("Failed to blacklist caller tokens on password change for user %s: %s", current_user.id, str(e))

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="PASSWORD_CHANGED",
        resource_type="user",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        org_id=current_user.org_id,
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": "Password changed successfully",
    }


# ── GET /users ─────────────────────────────────────────────────────────────


@router.get("/users", response_model=dict)
def list_users(
    skip: int = 0,
    limit: int = 20,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    if role and role not in ["admin", "staff", "vendor"]:
        raise ValidationError(f"Invalid role filter: {role}")
    if limit > 100:
        limit = 100  # Cap to prevent abuse

    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organization")
    target_org_id = current_user.org_id
    users = db.get_all_filtered(role=role, is_active=is_active, org_id=target_org_id, skip=skip, limit=limit)
    total = db.count_filtered(role=role, is_active=is_active, org_id=target_org_id)


    return {
        "success": True,
        "data": [_user_dict(u) for u in users],
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total,
        },
        "filters": {"role": role, "is_active": is_active},
    }


def _enforce_tenant_user_access(target_user: User, current_user: User) -> None:
    """
    Strict multi-tenant security barrier:
    - Tenant admins ('admin') are strictly constrained to their own organization (target_user.org_id == current_user.org_id).
    - Tenant admins can NEVER view, modify, reset, or delete users belonging to another organization.
    """
    if current_user.org_id is None or target_user.org_id != current_user.org_id:
        raise AuthorizationError("Cross-tenant operation denied: user belongs to another organization")


# ── GET /users/{user_id} ──────────────────────────────────────────────────


@router.get("/users/{user_id}", response_model=dict)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    user = db.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    _enforce_tenant_user_access(user, current_user)

    return {
        "success": True,
        "data": _user_dict(user),
    }


# ── PUT /users/{user_id} ──────────────────────────────────────────────────



@router.put("/users/{user_id}", response_model=dict)
def update_user_profile_by_admin(
    user_id: int,
    request_body: UserUpdate,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    """
    Update staff or vendor user details.
    Enforces tenant boundaries and validates that assigned location IDs belong to the organization.
    """
    user = db.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    _enforce_tenant_user_access(user, current_user)

    # 1. Email update & uniqueness
    if request_body.email and request_body.email.lower() != user.email.lower():
        existing_email = db.get_by_email(request_body.email)
        if existing_email and existing_email.id != user.id:
            raise DuplicateError(f"Email '{request_body.email}' is already registered")
        user.email = request_body.email.lower()

    # 2. Username update & uniqueness
    if request_body.username and request_body.username.strip().lower() != user.username.lower():
        existing_username = db.get_by_username(request_body.username.strip())
        if existing_username and existing_username.id != user.id:
            raise DuplicateError(f"Username '{request_body.username}' is already taken")
        user.username = request_body.username.strip()

    # 3. Full name
    if request_body.full_name is not None:
        user.full_name = request_body.full_name.strip()

    # 4. Role
    if request_body.role is not None:
        if request_body.role not in ["admin", "staff", "vendor"]:
            raise ValidationError(f"Invalid role: {request_body.role}")
        user.role = request_body.role

    # 5. Is active
    if request_body.is_active is not None:
        if user.id == current_user.id and not request_body.is_active:
            raise ValidationError("Cannot deactivate your own account")
        user.is_active = request_body.is_active

    # 6. Location assignments validation
    if request_body.location_ids is not None:
        loc_ids = request_body.location_ids
        target_org = user.org_id or current_user.org_id
        if loc_ids:
            if target_org is None:
                raise AuthorizationError("User is not assigned to an organization")
            valid_locs = db.db.query(Location.id).filter(
                Location.id.in_(loc_ids),
                Location.org_id == target_org,
            ).all()
            valid_set = {loc[0] for loc in valid_locs}
            invalid_ids = [lid for lid in loc_ids if lid not in valid_set]
            if invalid_ids:
                raise ValidationError(f"Invalid location ID(s): {invalid_ids}. Locations must belong to your organization.")
        user.location_ids = loc_ids

    db.update(user)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="USER_UPDATED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        org_id=user.org_id,
        details={"target_user": user.username},
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": f"User {user.username} updated successfully",
        "data": _user_dict(user),
    }


# ── PUT /users/{user_id}/role ─────────────────────────────────────────────



@router.put("/users/{user_id}/role", response_model=dict)
def update_user_role(
    user_id: int,
    request_body: RoleUpdate,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    user = db.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    _enforce_tenant_user_access(user, current_user)

    if request_body.role not in ["admin", "staff", "vendor"]:
        raise ValidationError(f"Invalid role: {request_body.role}")

    old_role = user.role
    user.role = request_body.role
    db.update(user)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="ROLE_CHANGED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        org_id=user.org_id,
        details={
            "target_user": user.username,
            "old_role": old_role,
            "new_role": user.role,
        },
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": f"User role updated to {request_body.role}",
        "data": _user_dict(user),
    }


# ── PUT /users/{user_id}/activate ─────────────────────────────────────────


@router.put("/users/{user_id}/activate", response_model=dict)
def activate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    user = db.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    _enforce_tenant_user_access(user, current_user)

    user.is_active = True
    db.update(user)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="USER_ACTIVATED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        org_id=user.org_id,
        details={"target_user": user.username},
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": f"User {user.username} activated",
    }


# ── PUT /users/{user_id}/deactivate ───────────────────────────────────────


@router.put("/users/{user_id}/deactivate", response_model=dict)
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    user = db.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    _enforce_tenant_user_access(user, current_user)

    if user.id == current_user.id:
        raise ValidationError("Cannot deactivate your own account")

    user.is_active = False
    db.update(user)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="USER_DEACTIVATED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        org_id=user.org_id,
        details={"target_user": user.username},
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": f"User {user.username} deactivated",
    }


# ── POST /users/{user_id}/reset-password ──────────────────────────────────


@router.post("/users/{user_id}/reset-password", response_model=dict)
def admin_reset_password(
    user_id: int,
    request_body: AdminPasswordReset,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    user = db.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    _enforce_tenant_user_access(user, current_user)

    user.hashed_password = hash_password(request_body.new_password)
    # Also unlock and reset attempts if they were locked
    user.login_attempts = 0
    user.locked_until = None
    db.update(user)

    # Invalidate existing sessions issued before this password reset
    try:
        from app.infrastructure.cache.redis_client import get_redis, is_redis_available
        r = get_redis()
        if r and is_redis_available():
            r.setex(f"user_pw_changed:{user.id}", 3600 * 24, str(int(time.time())))
    except Exception as e:
        logger.error("Failed to set user_pw_changed in Redis for user %s: %s", user.id, str(e))

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="PASSWORD_RESET_BY_ADMIN",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        org_id=user.org_id,
        details={"target_user": user.username},
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": f"Password for {user.username} has been reset",
    }


# ── DELETE /users/{user_id} ───────────────────────────────────────────────


@router.delete("/users/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_user_repo),
    current_user: User = Depends(require_admin),
):
    user = db.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    _enforce_tenant_user_access(user, current_user)

    if user.id == current_user.id:
        raise ValidationError("Cannot delete your own account")

    deleted_username = user.username
    db.delete(user_id)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=current_user.username,
        action="USER_DELETED",
        resource_type="user",
        resource_id=str(user_id),
        user_id=current_user.id,
        org_id=user.org_id,
        details={"deleted_user": deleted_username},
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": f"User {deleted_username} deleted",
    }



# ── POST /request-password-reset ────────────────────────────────────────────


@router.post("/request-password-reset", response_model=dict)
@limiter.limit("3/minute")
def request_password_reset(
    request: Request,
    request_body: dict,
    db: Session = Depends(get_user_repo),
):
    """Request a password reset link to be sent to user's email."""
    email = request_body.get("email")
    if not email:
        raise ValidationError("Email is required")

    user = db.get_by_email(email)

    # Always return success to prevent email enumeration
    # If user exists, send reset email; otherwise do nothing
    if user:
        _send_password_reset_email(user)

        audit = AuditService(db.db)
        audit.log(
            username=user.username,
            action="PASSWORD_RESET_REQUESTED",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
            org_id=user.org_id,
            details={"email": email},
            ip_address=_get_client_ip(request),
        )

    # Return same message whether user exists or not
    return {
        "success": True,
        "message": "If an account exists with this email, a password reset link has been sent.",
    }


# ── POST /reset-password ───────────────────────────────────────────────────


@router.post("/reset-password", response_model=dict)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    request_body: PasswordResetConfirmRequest,
    db: Session = Depends(get_user_repo),
):
    """Reset password using the token from email."""
    try:
        payload = jwt.decode(
            request_body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Password reset token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid password reset token")

    if payload.get("type") != "password_reset":
        raise AuthenticationError("Invalid token type")

    # ── Single-use check: consume the JTI atomically ──────────────────────
    jti = payload.get("jti")
    if not jti:
        raise AuthenticationError("Invalid password reset token: missing jti")
    from app.infrastructure.cache.token_blacklist import consume_reset_jti
    if not consume_reset_jti(jti):
        raise AuthenticationError("Password reset token has already been used or has expired")

    user_id = payload.get("sub")
    user = db.get_by_id(user_id)

    if not user:
        raise NotFoundError("User", user_id)

    # Verify email matches
    if user.email != payload.get("email"):
        raise AuthenticationError("Token does not match user email")

    # Update password
    user.hashed_password = hash_password(request_body.new_password)
    user.login_attempts = 0
    user.locked_until = None
    db.update(user)

    # ── Invalidate all existing sessions for this user ────────────────────
    # This ensures no stale access tokens work after a password reset.
    # We rely on the auth L1 cache eviction; Redis blacklisting of the
    # individual tokens requires the token strings, which we don't have here,
    # so instead we store a user-level invalidation marker.
    try:
        from app.infrastructure.cache.redis_client import get_redis, is_redis_available
        r = get_redis()
        if r and is_redis_available():
            # Mark this user's session as reset — dependencies.py can check this
            r.setex(f"user_pw_changed:{user.id}", 3600 * 24, str(int(time.time())))
    except Exception as e:
        logger.error("Failed to set user_pw_changed in Redis for user %s: %s", user.id, str(e))

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=user.username,
        action="PASSWORD_RESET_COMPLETED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        org_id=user.org_id,
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": "Password has been reset successfully. Please login with your new password.",
    }


# ── POST /verify-email ─────────────────────────────────────────────────────


@router.post("/verify-email", response_model=dict)
def verify_email(
    request: Request,
    request_body: VerifyEmailRequest,
    db: Session = Depends(get_user_repo),
):
    """Verify user's email using the token from the verification email."""
    try:
        payload = jwt.decode(
            request_body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Email verification token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid email verification token")

    if payload.get("type") != "email_verification":
        raise AuthenticationError("Invalid token type")

    user_id = payload.get("sub")
    user = db.get_by_id(user_id)

    if not user:
        raise NotFoundError("User", user_id)

    if user.is_verified:
        return {
            "success": True,
            "message": "Email is already verified",
        }

    # Verify email matches
    if user.email != payload.get("email"):
        raise AuthenticationError("Token does not match user email")

    # Mark as verified
    user.is_verified = True
    user.is_active = True  # Auto-activate after verification
    db.update(user)

    # Audit log
    audit = AuditService(db.db)
    audit.log(
        username=user.username,
        action="EMAIL_VERIFIED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        org_id=user.org_id,
        ip_address=_get_client_ip(request),
    )

    return {
        "success": True,
        "message": "Email verified successfully. Your account is now active.",
    }


# ── POST /google-auth ──────────────────────────────────────────────────────


@router.post("/google-auth")
@limiter.limit(settings.RATE_LIMIT_AUTH)
def google_auth(
    request: Request,
    response: Response,
    request_body: GoogleAuthRequest,
    db: Session = Depends(get_user_repo),
):
    """Authenticate or register user via Google OAuth (ID token or OAuth2 access token)."""
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    if not client_id:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Google OAuth is not configured on this server.",
                },
            },
        )

    token_str = (request_body.id_token or "").strip()
    if not token_str:
        raise AuthenticationError("Google token is required")

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        id_info = google_id_token.verify_oauth2_token(
            token_str,
            google_requests.Request(),
            client_id,
        )
    except ValueError as ve:
        # If verify_oauth2_token fails, attempt OAuth2 access token verification via Google APIs
        try:
            import httpx
            # Verify token audience with Google tokeninfo
            tokeninfo_res = httpx.get(
                f"https://oauth2.googleapis.com/tokeninfo?access_token={token_str}",
                timeout=10.0,
            )
            if tokeninfo_res.status_code != 200:
                raise AuthenticationError(f"Invalid Google ID token: {str(ve)}")
            tokeninfo_data = tokeninfo_res.json()

            token_aud = (
                tokeninfo_data.get("azp")
                or tokeninfo_data.get("aud")
                or tokeninfo_data.get("issued_to")
                or tokeninfo_data.get("audience")
            )
            if client_id and token_aud and token_aud != client_id and tokeninfo_data.get("azp") != client_id and tokeninfo_data.get("aud") != client_id:
                logger.warning("Token audience mismatch: got %s (azp=%s, aud=%s), expected %s", token_aud, tokeninfo_data.get("azp"), tokeninfo_data.get("aud"), client_id)
                raise AuthenticationError("Google access token audience mismatch")

            # Fetch user profile from userinfo
            userinfo_res = httpx.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_str}"},
                timeout=10.0,
            )
            userinfo_data = userinfo_res.json() if userinfo_res.status_code == 200 else {}

            id_info = {
                "email": userinfo_data.get("email") or tokeninfo_data.get("email"),
                "email_verified": userinfo_data.get("email_verified", tokeninfo_data.get("email_verified", True)),
                "name": userinfo_data.get("name", tokeninfo_data.get("name", "")),
                "sub": userinfo_data.get("sub") or tokeninfo_data.get("sub"),
                "iss": "https://accounts.google.com",
                "aud": client_id,
            }
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Google Access Token verification failed: %s", str(e))
            raise AuthenticationError("Google access token verification failed")
    except Exception as e:
        logger.error("Google OAuth token verification failed: %s", str(e))
        raise AuthenticationError("Google ID token verification failed")

    google_email = id_info.get("email")
    google_name = id_info.get("name", "")

    if not google_email:
        raise AuthenticationError("Google account has no email")

    # Mandatory claims verification: email_verified, issuer, audience
    email_verified = id_info.get("email_verified")
    if email_verified is None or str(email_verified).lower() not in ["true", "1"]:
        raise AuthenticationError("Google account email is not verified")

    iss = id_info.get("iss")
    if not iss or iss not in ["accounts.google.com", "https://accounts.google.com"]:
        raise AuthenticationError("Invalid Google ID token issuer")

    aud = id_info.get("aud")
    if not aud or aud != client_id:
        raise AuthenticationError("Google ID token audience mismatch")

    if user:
        # Existing user - log them in
        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        db.record_login(user)

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "username": user.username,
                "role": user.role,
                "org_id": user.org_id,
            }
        )
        refresh_token = create_refresh_token(
            {"sub": str(user.id), "username": user.username}
        )

        # Set HttpOnly, SameSite cookies
        _set_auth_cookies(response, access_token, refresh_token)

        audit = AuditService(db.db)
        audit.log(
            username=user.username,
            action="GOOGLE_LOGIN",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
            org_id=user.org_id,
            ip_address=_get_client_ip(request),
        )

        json_resp = JSONResponse(
            content={
                "success": True,
                "message": "Login successful",
                "data": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": _user_dict(user),
                },
            }
        )
        _set_auth_cookies(json_resp, access_token, refresh_token)
        return json_resp

    # New user - create account
    from app.infrastructure.database.models import Organization, Location
    import secrets

    # Generate a unique username from email
    base_username = google_email.split("@")[0].lower().replace(".", "_")
    username = base_username
    counter = 1
    while db.get_by_username(username):
        username = f"{base_username}_{counter}"
        counter += 1

    # Create Organization for regular tenant user
    base_slug = username.replace("_", "-")
    slug = base_slug
    counter = 1
    while db.db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org_name = f"{google_name or username}'s Pharmacy & Medical Store"
    new_org = Organization(name=org_name, slug=slug, is_active=True)
    db.db.add(new_org)
    db.db.commit()
    db.db.refresh(new_org)

    # Create default Main Pharmacy Counter location
    default_location = Location(
        org_id=new_org.id,
        name=f"{google_name or username} - Main Counter",
        type="retail_counter",
        region="Default Region",
        address="Main Store Location",
    )
    db.db.add(default_location)
    db.db.commit()
    db.db.refresh(default_location)

    assigned_org_id = new_org.id
    assigned_locs = [default_location.id]
    role = "admin"

    # Create user with Google OAuth
    user = db.create(
        email=google_email,
        username=username,
        password=secrets.token_urlsafe(32),  # Random secure password
        full_name=google_name,
        role=role,
        org_id=assigned_org_id,
        location_ids=assigned_locs,
    )

    user.is_verified = True
    user.is_active = True
    db.update(user)

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "org_id": user.org_id,
        }
    )
    refresh_token = create_refresh_token(
        {"sub": str(user.id), "username": user.username}
    )

    audit = AuditService(db.db)
    audit.log(
        username=user.username,
        action="GOOGLE_REGISTER",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        org_id=user.org_id,
        details={"email": google_email},
        ip_address=_get_client_ip(request),
    )

    # Dispatch welcome email to user's Gmail
    try:
        NotificationService.send_admin_congratulations_email(
            to_email=user.email,
            username=user.username,
            full_name=user.full_name,
            organization_name=org_name,
        )
    except Exception as mail_err:
        logger.warning("Could not dispatch welcome email on Google signup: %s", mail_err)

    # Asynchronously index onboarding context into Vector Memory
    if user.org_id:
        try:
            from app.workers.tasks import sync_onboarding_context_task
            sync_onboarding_context_task.delay(
                org_id=user.org_id,
                user_id=user.id,
                full_name=user.full_name or user.username,
                pharmacy_name=org_name,
                primary_counter="Main Market Counter",
                plan_type="single_pharmacy",
                extra_settings={"primary_counter_name": "Main Market Counter"},
            )
        except Exception as vec_err:
            logger.warning("Could not queue vector memory sync on Google signup: %s", vec_err)

    json_resp = JSONResponse(
        content={
            "success": True,
            "message": "Account created successfully via Google",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": _user_dict(user),
            },
        }
    )
    _set_auth_cookies(json_resp, access_token, refresh_token)
    return json_resp


