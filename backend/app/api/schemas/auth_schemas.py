from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="staff")


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    """Used by PATCH /auth/me — users update their own profile."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=200)


class AdminPasswordReset(BaseModel):
    """Admin resets another user's password."""
    new_password: str = Field(..., min_length=8, max_length=100)


class UserResponse(UserBase):
    id: int
    role: str
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
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|manager|staff|viewer)$")
