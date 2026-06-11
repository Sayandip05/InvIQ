"""
FastAPI dependency injection factories.

Implements the FastAPI tutorial OAuth2 + JWT pattern:
  https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/

get_current_user() receives token: str = Depends(oauth2_scheme)
where oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login").
This wires up the Swagger /docs "Authorize" button automatically.

Route handlers use Depends() to receive pre-validated user objects.
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.requisition_repo import RequisitionRepository
from app.infrastructure.database.user_repo import UserRepository
from app.application.inventory_service import InventoryService
from app.application.requisition_service import RequisitionService
from app.core.security import oauth2_scheme, verify_access_token, check_role_permission
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.infrastructure.database.models import User


# ── Repository factories ───────────────────────────────────────────────────


def get_inventory_repo(db: Session = Depends(get_db)) -> InventoryRepository:
    return InventoryRepository(db)


def get_requisition_repo(db: Session = Depends(get_db)) -> RequisitionRepository:
    return RequisitionRepository(db)


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_db_session(db: Session = Depends(get_db)) -> Session:
    """Raw database session for direct DB operations."""
    return db


def get_inventory_service(
    repo: InventoryRepository = Depends(get_inventory_repo),
) -> InventoryService:
    return InventoryService(repo)


def get_requisition_service(
    repo: RequisitionRepository = Depends(get_requisition_repo),
    inv_repo: InventoryRepository = Depends(get_inventory_repo),
) -> RequisitionService:
    return RequisitionService(repo, inv_repo)


# ── Authentication dependency (FastAPI tutorial pattern) ───────────────────


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """
    Decode and validate the Bearer JWT token on every protected request.

    Follows the FastAPI OAuth2 + JWT tutorial exactly:
      1. OAuth2PasswordBearer extracts Bearer token from Authorization header
      2. PyJWT decodes and verifies signature + expiry
      3. Token blacklist check (logout support)
      4. User lookup from DB to ensure account still active

    Raises HTTP 401 on any failure with WWW-Authenticate: Bearer header.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # ── Check token blacklist (invalidated on logout) ──────────────
        from app.infrastructure.cache.token_blacklist import is_token_blacklisted

        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ── Decode and verify JWT ──────────────────────────────────────
        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # ── Load user from database ────────────────────────────────────
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if user is None:
            raise credentials_exception
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise credentials_exception


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Optional authentication dependency for Guest Demo Mode endpoints.

    Reads the Authorization header and attempts JWT validation.
    Returns the authenticated User object if the token is valid, or
    None (silently) when:
      - No Authorization header / token is present
      - Token is expired, malformed, or on the blacklist
      - The referenced user no longer exists or is inactive

    Unlike get_current_user(), this dependency NEVER raises HTTP 401.
    Use it on GET endpoints that should be readable by unauthenticated
    guests while still identifying authenticated callers if present.
    """
    from app.infrastructure.cache.token_blacklist import is_token_blacklisted

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    if not token:
        return None

    try:
        if is_token_blacklisted(token):
            return None

        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            return None

        return user
    except Exception:
        # Any JWT or DB failure → silently treat caller as guest
        return None


# ── Active user shorthand ──────────────────────────────────────────────────


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Shorthand — get current user and assert account is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ── Role-based access control ──────────────────────────────────────────────


def require_role(required_role: str):
    """Factory that returns a dependency requiring minimum role level."""

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not check_role_permission(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Requires '{required_role}' role or higher.",
            )
        return current_user

    return role_checker


def require_admin(
    current_user: Annotated[User, Depends(require_role("admin"))],
) -> User:
    return current_user


def require_manager(
    current_user: Annotated[User, Depends(require_role("manager"))],
) -> User:
    return current_user


def require_staff(
    current_user: Annotated[User, Depends(require_role("staff"))],
) -> User:
    return current_user


def require_super_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Only the platform super_admin can access these endpoints."""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required.",
        )
    return current_user


def require_vendor(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Vendor or higher role."""
    if current_user.role not in {"vendor", "staff", "manager", "admin", "super_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor access required.",
        )
    return current_user
