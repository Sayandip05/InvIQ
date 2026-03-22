from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger("smart_inventory.security")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning("JWT decode error: %s", str(e))
        raise AuthenticationError("Invalid or expired token")


def verify_access_token(token: str) -> Dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")
    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token")
    return payload


ALLOWED_ROLES = {"admin", "manager", "staff", "viewer"}
ROLE_HIERARCHY = {
    "admin": 4,
    "manager": 3,
    "staff": 2,
    "viewer": 1,
}


def check_role_permission(user_role: str, required_role: str) -> bool:
    if user_role not in ALLOWED_ROLES or required_role not in ALLOWED_ROLES:
        return False
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)
