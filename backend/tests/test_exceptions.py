"""
Exception tests — custom exception hierarchy.

Tests the core/exceptions.py module.
"""

import pytest
from app.core.exceptions import (
    AppException,
    NotFoundError,
    ValidationError,
    InsufficientStockError,
    DuplicateError,
    InvalidStateError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
)


class TestAppException:
    """Test base application exception."""

    def test_app_exception_default(self):
        """AppException should have default message."""
        exc = AppException()
        assert exc.message == "An unexpected error occurred"
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"

    def test_app_exception_custom_message(self):
        """AppException should accept custom message."""
        exc = AppException("Custom error message")
        assert exc.message == "Custom error message"
        assert str(exc) == "Custom error message"


class TestNotFoundError:
    """Test NotFoundError exception."""

    def test_not_found_error_default(self):
        """NotFoundError should have default message."""
        exc = NotFoundError()
        assert "Resource not found" in exc.message
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"

    def test_not_found_error_with_resource(self):
        """NotFoundError should format resource name."""
        exc = NotFoundError("User")
        assert "User not found" in exc.message

    def test_not_found_error_with_identifier(self):
        """NotFoundError should include identifier."""
        exc = NotFoundError("Item", 123)
        assert "Item with id '123' not found" in exc.message


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error(self):
        """ValidationError should have correct status."""
        exc = ValidationError("Invalid input data")
        assert exc.message == "Invalid input data"
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"


class TestInsufficientStockError:
    """Test InsufficientStockError exception."""

    def test_insufficient_stock_error(self):
        """InsufficientStockError should have correct status."""
        exc = InsufficientStockError("Not enough stock available")
        assert exc.message == "Not enough stock available"
        assert exc.status_code == 400
        assert exc.error_code == "INSUFFICIENT_STOCK"


class TestDuplicateError:
    """Test DuplicateError exception."""

    def test_duplicate_error(self):
        """DuplicateError should have correct status."""
        exc = DuplicateError("Resource already exists")
        assert exc.message == "Resource already exists"
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE"


class TestInvalidStateError:
    """Test InvalidStateError exception."""

    def test_invalid_state_error_default(self):
        """InvalidStateError should have default message."""
        exc = InvalidStateError()
        assert "Operation not allowed in current state" in exc.message
        assert exc.status_code == 400
        assert exc.error_code == "INVALID_STATE"

    def test_invalid_state_error_custom(self):
        """InvalidStateError should accept custom message."""
        exc = InvalidStateError("Cannot approve already approved requisition")
        assert exc.message == "Cannot approve already approved requisition"


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_default(self):
        """AuthenticationError should have default message."""
        exc = AuthenticationError()
        assert exc.message == "Invalid credentials"
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"

    def test_authentication_error_custom(self):
        """AuthenticationError should accept custom message."""
        exc = AuthenticationError("Token expired")
        assert exc.message == "Token expired"


class TestAuthorizationError:
    """Test AuthorizationError exception."""

    def test_authorization_error_default(self):
        """AuthorizationError should have default message."""
        exc = AuthorizationError()
        assert exc.message == "Insufficient permissions"
        assert exc.status_code == 403
        assert exc.error_code == "AUTHORIZATION_ERROR"

    def test_authorization_error_custom(self):
        """AuthorizationError should accept custom message."""
        exc = AuthorizationError("Admin access required")
        assert exc.message == "Admin access required"


class TestDatabaseError:
    """Test DatabaseError exception."""

    def test_database_error_default(self):
        """DatabaseError should have default message."""
        exc = DatabaseError()
        assert exc.message == "A database error occurred"
        assert exc.status_code == 500
        assert exc.error_code == "DATABASE_ERROR"

    def test_database_error_custom(self):
        """DatabaseError should accept custom message."""
        exc = DatabaseError("Connection timeout")
        assert exc.message == "Connection timeout"


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_inherit_from_app_exception(self):
        """All custom exceptions should inherit from AppException."""
        assert issubclass(NotFoundError, AppException)
        assert issubclass(ValidationError, AppException)
        assert issubclass(InsufficientStockError, AppException)
        assert issubclass(DuplicateError, AppException)
        assert issubclass(InvalidStateError, AppException)
        assert issubclass(AuthenticationError, AppException)
        assert issubclass(AuthorizationError, AppException)
        assert issubclass(DatabaseError, AppException)

    def test_all_inherit_from_exception(self):
        """All custom exceptions should inherit from base Exception."""
        assert issubclass(AppException, Exception)
        assert issubclass(NotFoundError, Exception)
        assert issubclass(ValidationError, Exception)
