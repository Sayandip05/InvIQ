"""
Standardized API response schemas.

All endpoints should return one of these models to ensure
consistent response shapes across the entire API.
"""

from pydantic import BaseModel
from typing import Any, Optional


class APIResponse(BaseModel):
    """Standard response for all endpoints."""

    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None


class PaginatedResponse(APIResponse):
    """Response with pagination metadata."""

    page: int = 1
    page_size: int = 20
    total: int = 0

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class ErrorDetail(BaseModel):
    """Structured error detail inside an error response."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error response shape (matches what global error handlers return)."""

    success: bool = False
    error: ErrorDetail
