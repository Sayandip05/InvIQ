"""
Security module tests — password hashing, JWT tokens, role hierarchy.

Tests the core/security.py module in isolation.
"""

import pytest
from datetime import timedelta
import jwt

from app.core.security import (
    hash_password,
    verify_password,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_access_token,
    verify_refresh_token,
    check_role_permission,
    ROLE_HIERARCHY,
    ALLOWED_ROLES,
)
from app.core.exceptions import AuthenticationError
from app.core.config import settings


class TestPasswordHashing:
    """Test Argon2 password hashing and verification."""

    def test_hash_password_returns_different_hash(self):
        """Same password should produce different hashes (salt)."""
        password = "TestPass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert len(hash1) > 50  # Argon2 hashes are long

    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        password = "MySecurePass456"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Wrong password should fail verification."""
        password = "CorrectPassword"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty(self):
        """Empty password should fail verification."""
        hashed = hash_password("RealPassword")
        assert verify_password("", hashed) is False

    def test_hash_password_special_characters(self):
        """Password with special characters should hash correctly."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


class TestAuthenticateUser:
    """Test user authentication with timing attack prevention."""

    def test_authenticate_user_success(self, test_user):
        """Valid user and password should authenticate."""
        user = test_user["user"]
        result = authenticate_user(user, test_user["password"])
        assert result is True

    def test_authenticate_user_wrong_password(self, test_user):
        """Wrong password should fail authentication."""
        user = test_user["user"]
        result = authenticate_user(user, "wrongpassword")
        assert result is False

    def test_authenticate_user_none(self):
        """None user should fail authentication (timing-safe)."""
        result = authenticate_user(None, "anypassword")
        assert result is False


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Access token should be created with correct payload."""
        data = {"sub": "123", "username": "testuser", "role": "staff"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 50

        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"
        assert payload["role"] == "staff"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token(self):
        """Refresh token should be created with correct payload."""
        data = {"sub": "456", "username": "refreshuser"}
        token = create_refresh_token(data)
        assert isinstance(token, str)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "456"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_create_token_with_custom_expiry(self):
        """Token with custom expiry should respect the delta."""
        data = {"sub": "789"}
        token = create_access_token(data, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_decode_token_valid(self):
        """Valid token should decode successfully."""
        data = {"sub": "100", "username": "decodetest"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "100"
        assert payload["username"] == "decodetest"

    def test_decode_token_invalid_signature(self):
        """Token with invalid signature should raise AuthenticationError."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid"
        with pytest.raises(AuthenticationError):
            decode_token(token)

    def test_decode_token_malformed(self):
        """Malformed token should raise AuthenticationError."""
        with pytest.raises(AuthenticationError):
            decode_token("not.a.token")

    def test_verify_access_token_success(self):
        """Access token should verify with correct type."""
        data = {"sub": "200", "username": "accesstest"}
        token = create_access_token(data)
        payload = verify_access_token(token)
        assert payload["type"] == "access"
        assert payload["sub"] == "200"

    def test_verify_access_token_wrong_type(self):
        """Refresh token should fail access token verification."""
        data = {"sub": "300"}
        token = create_refresh_token(data)
        with pytest.raises(AuthenticationError, match="expected access token"):
            verify_access_token(token)

    def test_verify_refresh_token_success(self):
        """Refresh token should verify with correct type."""
        data = {"sub": "400", "username": "refreshtest"}
        token = create_refresh_token(data)
        payload = verify_refresh_token(token)
        assert payload["type"] == "refresh"
        assert payload["sub"] == "400"

    def test_verify_refresh_token_wrong_type(self):
        """Access token should fail refresh token verification."""
        data = {"sub": "500"}
        token = create_access_token(data)
        with pytest.raises(AuthenticationError, match="expected refresh token"):
            verify_refresh_token(token)


class TestRoleHierarchy:
    """Test role-based access control hierarchy."""

    def test_role_hierarchy_structure(self):
        """Role hierarchy should have correct levels."""
        assert ROLE_HIERARCHY["super_admin"] == 6
        assert ROLE_HIERARCHY["admin"] == 5
        assert ROLE_HIERARCHY["manager"] == 4
        assert ROLE_HIERARCHY["staff"] == 3
        assert ROLE_HIERARCHY["vendor"] == 2
        assert ROLE_HIERARCHY["viewer"] == 1

    def test_allowed_roles_set(self):
        """Allowed roles should match hierarchy keys."""
        assert ALLOWED_ROLES == {"super_admin", "admin", "manager", "staff", "vendor", "viewer"}

    def test_check_role_permission_same_level(self):
        """User with same role level should have permission."""
        assert check_role_permission("staff", "staff") is True
        assert check_role_permission("admin", "admin") is True

    def test_check_role_permission_higher_level(self):
        """User with higher role should have permission."""
        assert check_role_permission("admin", "staff") is True
        assert check_role_permission("manager", "viewer") is True
        assert check_role_permission("super_admin", "admin") is True

    def test_check_role_permission_lower_level(self):
        """User with lower role should not have permission."""
        assert check_role_permission("staff", "admin") is False
        assert check_role_permission("viewer", "manager") is False
        assert check_role_permission("vendor", "staff") is False

    def test_check_role_permission_invalid_user_role(self):
        """Invalid user role should deny permission."""
        assert check_role_permission("invalid_role", "staff") is False

    def test_check_role_permission_invalid_required_role(self):
        """Invalid required role should deny permission."""
        assert check_role_permission("admin", "invalid_role") is False

    def test_check_role_permission_both_invalid(self):
        """Both invalid roles should deny permission."""
        assert check_role_permission("fake", "notreal") is False

    def test_super_admin_has_all_permissions(self):
        """Super admin should have permission for all roles."""
        for role in ALLOWED_ROLES:
            assert check_role_permission("super_admin", role) is True

    def test_viewer_has_minimal_permissions(self):
        """Viewer should only have permission for viewer role."""
        assert check_role_permission("viewer", "viewer") is True
        assert check_role_permission("viewer", "staff") is False
        assert check_role_permission("viewer", "admin") is False
