"""
Security module tests — password hashing, JWT tokens, role hierarchy, email masking.
Tests core/security.py in isolation with consolidated, high-signal test cases.
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
    mask_email,
)
from app.core.exceptions import AuthenticationError
from app.core.config import settings


class TestPasswordHashingAndAuth:
    """Test Argon2 password hashing and timing-safe authentication."""

    def test_password_hashing_and_verification(self):
        """Test hashing salting, correct verification, and invalid password rejection."""
        password = "MySecurePass456!#$"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert len(hash1) > 50

        assert verify_password(password, hash1) is True
        assert verify_password("WrongPassword", hash1) is False
        assert verify_password("", hash1) is False

    def test_authenticate_user_flows(self, test_user):
        """Test valid user authentication, wrong password, and timing-safe None user."""
        user = test_user["user"]
        assert authenticate_user(user, test_user["password"]) is True
        assert authenticate_user(user, "wrongpassword") is False
        assert authenticate_user(None, "anypassword") is False


class TestJWTTokens:
    """Test JWT token creation, expiration, type verification, and tampering rejection."""

    def test_access_and_refresh_token_lifecycle(self):
        """Test creating, decoding, and validating access and refresh tokens."""
        # 1. Access Token
        access_token = create_access_token({"sub": "123", "username": "testuser", "role": "staff"})
        payload = decode_token(access_token)
        assert payload["sub"] == "123"
        assert payload["role"] == "staff"
        assert payload["type"] == "access"
        assert verify_access_token(access_token)["sub"] == "123"

        # 2. Refresh Token
        refresh_token = create_refresh_token({"sub": "456", "username": "refreshuser"})
        ref_payload = decode_token(refresh_token)
        assert ref_payload["type"] == "refresh"
        assert verify_refresh_token(refresh_token)["sub"] == "456"

        # 3. Cross-type rejection
        with pytest.raises(AuthenticationError, match="expected access token"):
            verify_access_token(refresh_token)
        with pytest.raises(AuthenticationError, match="expected refresh token"):
            verify_refresh_token(access_token)

    def test_invalid_tokens_raise_authentication_error(self):
        """Test invalid signature and malformed tokens."""
        with pytest.raises(AuthenticationError):
            decode_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid")
        with pytest.raises(AuthenticationError):
            decode_token("not.a.token")


class TestRoleHierarchy:
    """Test role-based access control hierarchy matrix."""

    def test_role_hierarchy_permissions(self):
        """Verify role hierarchy matrix and permission boundaries."""
        assert "super_admin" not in ROLE_HIERARCHY
        assert ROLE_HIERARCHY["admin"] == 3
        assert ROLE_HIERARCHY["staff"] == 2
        assert ROLE_HIERARCHY["vendor"] == 1
        assert ALLOWED_ROLES == {"admin", "staff", "vendor"}

        # Admin has top permissions
        for role in ALLOWED_ROLES:
            assert check_role_permission("admin", role) is True

        # Same level & lower level checks
        assert check_role_permission("admin", "staff") is True
        assert check_role_permission("staff", "staff") is True
        assert check_role_permission("staff", "admin") is False
        assert check_role_permission("vendor", "staff") is False

        # Invalid roles
        assert check_role_permission("invalid_role", "staff") is False
        assert check_role_permission("admin", "invalid_role") is False


class TestEmailMaskingAndUploadSecurity:
    """Test PII email masking and file upload boundaries."""

    def test_mask_email(self):
        """Test masking standard, short, and invalid email inputs."""
        assert mask_email("sayandip@inviq.io") == "s***p@inviq.io"
        assert mask_email("admin@inventory.local") == "a***n@inventory.local"
        assert mask_email("a@example.com") == "a*@example.com"
        assert mask_email(None) is None
        assert mask_email("") == ""

    def test_transcribe_rejects_invalid_files(self, client, test_user):
        """Ensure audio transcribe endpoint rejects invalid MIME types and empty files."""
        import io
        from tests.conftest import get_auth_header
        headers = get_auth_header(client, test_user["username"], test_user["password"])

        fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" * 10)
        res1 = client.post("/api/chat/transcribe", files={"file": ("malicious.exe", fake_exe, "application/x-msdownload")}, headers=headers)
        assert res1.status_code in [400, 422]

        empty_file = io.BytesIO(b"")
        res2 = client.post("/api/chat/transcribe", files={"file": ("empty.webm", empty_file, "audio/webm")}, headers=headers)
        assert res2.status_code in [400, 422]
