"""
Security utilities — JWT tokens + password hashing.

Libraries (matching FastAPI official tutorial):
  - PyJWT        → JWT encode/verify
  - pwdlib[argon2] → Argon2 password hashing (GPU-resistant)

Key security features beyond the tutorial:
  - Token type enforcement (access vs refresh)
  - DUMMY_HASH for timing-attack prevention (username enumeration protection)
  - Role hierarchy enforcement
  - OAuth2PasswordBearer declared for Swagger UI /docs auto-auth
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger("smart_inventory.security")

# ── Password hashing (Argon2 — winner of Password Hashing Competition) ────
# Uses recommended settings: memory-hard, resistant to GPU/ASIC attacks
password_hash = PasswordHash.recommended()

# ── Timing attack prevention ───────────────────────────────────────────────
# Always run a hash verify even if user doesn't exist, so an attacker
# cannot enumerate valid usernames via response timing differences.
# See: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
DUMMY_HASH = password_hash.hash("dummypassword_not_used_ever")

# ── OAuth2 scheme — enables Swagger /docs "Authorize" button ──────────────
# Even though we use JSON login (not form data), declaring this makes
# the OpenAPI spec expose the Bearer token flow correctly.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Password utilities ────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its hash.

    Always runs in constant time — safe against timing attacks.
    """
    return password_hash.verify(plain_password, hashed_password)


def authenticate_user(user, plain_password: str) -> bool:
    """
    Authenticate a user object against a plaintext password.

    If user is None (username not found), still runs verify_password
    against DUMMY_HASH to prevent username enumeration via timing.

    Returns True if authentication succeeds, False otherwise.
    """
    if user is None:
        # Constant-time dummy check — prevents timing-based username enumeration
        verify_password(plain_password, DUMMY_HASH)
        return False
    return verify_password(plain_password, user.hashed_password)


# ── JWT token utilities ───────────────────────────────────────────────────

def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token.

    Payload includes:
      sub       → user ID (as string, per JWT spec)
      username  → for display without extra DB lookup
      role      → for RBAC checks without extra DB lookup
      type      → "access" sentinel to prevent refresh tokens being used as access
      exp       → expiry timestamp
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT refresh token.

    Longer-lived than access tokens. The "type": "refresh" sentinel
    prevents refresh tokens from being used to access protected endpoints.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token signature + expiry.

    Raises AuthenticationError on any failure (expired, tampered, malformed).
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except InvalidTokenError as e:
        logger.warning("JWT decode error: %s", str(e))
        raise AuthenticationError("Invalid or expired token")


def verify_access_token(token: str) -> Dict[str, Any]:
    """Decode and assert token type is 'access'."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type — expected access token")
    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """Decode and assert token type is 'refresh'."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid token type — expected refresh token")
    return payload


# ── Role hierarchy ────────────────────────────────────────────────────────

ALLOWED_ROLES = {"admin", "manager", "staff", "viewer"}
ROLE_HIERARCHY = {
    "admin": 4,
    "manager": 3,
    "staff": 2,
    "viewer": 1,
}


def check_role_permission(user_role: str, required_role: str) -> bool:
    """Return True if user_role meets or exceeds the required_role level."""
    if user_role not in ALLOWED_ROLES or required_role not in ALLOWED_ROLES:
        return False
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)
