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


import logging
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("smart_inventory.dependencies")


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode and validate the Bearer JWT token or HttpOnly cookie on every protected request.
    Verifies JWT signature, expiration, and blacklisting on every request.
    Loads and returns the User entity bound to the active request database session.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise credentials_exception

    try:
        # 1. Cryptographic verification of JWT (signature, expiry) on EVERY request
        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # 2. Check token blacklist (invalidated on logout)
        from app.infrastructure.cache.token_blacklist import is_token_blacklisted
        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Check password reset marker (invalidates tokens issued before password change)
        try:
            from app.infrastructure.cache.redis_client import get_redis, is_redis_available
            r = get_redis()
            if r and is_redis_available():
                pw_changed_ts = r.get(f"user_pw_changed:{user_id}")
                if pw_changed_ts:
                    token_iat = payload.get("iat", 0)
                    if token_iat < int(pw_changed_ts):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Session invalidated after password reset. Please log in again.",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
        except HTTPException:
            raise
        except Exception:
            pass  # Redis unavailable — don't break auth

        # 4. Load User attached to the current request's active DB session
        uid_int = int(user_id)
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(uid_int)
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
    except SQLAlchemyError as se:
        logger.error("Database connection error in get_current_user: %s", str(se))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable",
        )
    except Exception as e:
        logger.error("Unexpected error in get_current_user: %s", str(e))
        raise credentials_exception


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
    """Factory for role-based route protection."""

    def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
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


def require_staff(
    current_user: Annotated[User, Depends(require_role("staff"))],
) -> User:
    return current_user


def require_vendor(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Vendor or higher role (vendor → staff → admin)."""
    if not check_role_permission(current_user.role, "vendor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor access required.",
        )
    return current_user


def get_caller_org_id(user: User) -> int:
    """
    Return org_id for tenant-scoped operations.
    Every user (including admins) belongs strictly to their own organization.
    If org_id is None, raises AuthorizationError (403).
    Cross-tenant access is strictly forbidden.
    """
    if user.org_id is None:
        raise AuthorizationError("User is not assigned to an organization")
    return user.org_id


