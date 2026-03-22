"""
FastAPI dependency injection factories.

Route handlers use Depends() to receive pre-configured service instances
instead of creating them manually. This decouples routes from implementation
details and makes testing easy (swap repos with mocks).

Usage in routes:
    from app.core.dependencies import get_inventory_service

    @router.get("/items")
    def list_items(service: InventoryService = Depends(get_inventory_service)):
        return service.get_all_items()
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.infrastructure.database.connection import get_db
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.requisition_repo import RequisitionRepository
from app.infrastructure.database.user_repo import UserRepository
from app.application.inventory_service import InventoryService
from app.application.requisition_service import RequisitionService
from app.core.security import verify_access_token, check_role_permission
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.infrastructure.database.models import User

security = HTTPBearer()


def get_inventory_repo(db: Session = Depends(get_db)) -> InventoryRepository:
    return InventoryRepository(db)


def get_requisition_repo(db: Session = Depends(get_db)) -> RequisitionRepository:
    return RequisitionRepository(db)


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_inventory_service(
    repo: InventoryRepository = Depends(get_inventory_repo),
) -> InventoryService:
    return InventoryService(repo)


def get_requisition_service(
    repo: RequisitionRepository = Depends(get_requisition_repo),
    inv_repo: InventoryRepository = Depends(get_inventory_repo),
) -> RequisitionService:
    return RequisitionService(repo, inv_repo)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        token = credentials.credentials

        # ── Check if token has been blacklisted (logout) ──────────────
        from app.infrastructure.cache.token_blacklist import is_token_blacklisted
        if is_token_blacklisted(token):
            raise AuthenticationError("Token has been revoked")

        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found")
        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        return user
    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError("Could not validate credentials")


def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not check_role_permission(current_user.role, required_role):
            raise AuthorizationError(f"Requires {required_role} role or higher")
        return current_user

    return role_checker


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
    return current_user


def require_admin(current_user: User = Depends(require_role("admin"))) -> User:
    return current_user


def require_manager(current_user: User = Depends(require_role("manager"))) -> User:
    return current_user


def require_staff(current_user: User = Depends(require_role("staff"))) -> User:
    return current_user


def require_viewer(current_user: User = Depends(require_role("viewer"))) -> User:
    return current_user
