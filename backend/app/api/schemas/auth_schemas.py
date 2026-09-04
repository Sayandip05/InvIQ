from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
import re


# ── Shared password strength validator ────────────────────────────────────────

def _validate_password_strength(v: str) -> str:
    """Enforce minimum password complexity for all password fields.

    Requires: 8+ chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character.
    Called via @field_validator on every schema that accepts a password input.
    """
    errors = []
    if len(v) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", v):
        errors.append("one uppercase letter")
    if not re.search(r"[a-z]", v):
        errors.append("one lowercase letter")
    if not re.search(r"\d", v):
        errors.append("one digit (0-9)")
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]', v):
        errors.append("one special character (!@#$%^&*...)")
    if errors:
        raise ValueError(f"Password must contain: {', '.join(errors)}")
    return v


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    role: Optional[str] = Field(default=None, pattern="^(admin|staff|vendor)$")
    location_ids: Optional[List[int]] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|staff|vendor)$")
    is_active: Optional[bool] = None
    location_ids: Optional[List[int]] = None


class UserProfileUpdate(BaseModel):
    """Used by PATCH /auth/me — users update their own profile."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=200)


class AdminPasswordReset(BaseModel):
    """Admin resets another user's password."""

    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserResponse(UserBase):
    id: int
    org_id: Optional[int] = None
    role: str
    location_ids: Optional[List[int]] = None
    organization_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True



class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[datetime] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = (v or "").strip().lower()
        if "@" not in clean or len(clean.split("@")) != 2 or not clean.split("@")[0] or not clean.split("@")[1]:
            raise ValueError("A valid email address containing '@' is required")
        return clean




class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|staff|vendor)$")


class VerifyEmailRequest(BaseModel):
    token: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class GoogleAuthRequest(BaseModel):
    id_token: str

