"""
Custom exception hierarchy for the Smart Inventory Assistant.

All app-level exceptions inherit from AppException, which carries
a status_code, error_code, and human-readable message. FastAPI's
global error handler (registered in main.py) catches these and
returns a consistent JSON response.
"""


class AppException(Exception):
    """Base application exception."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found (404)."""

    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, resource: str = "Resource", identifier=None):
        detail = f"{resource} not found"
        if identifier is not None:
            detail = f"{resource} with id '{identifier}' not found"
        super().__init__(detail)


class ValidationError(AppException):
    """Invalid input data (422)."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class InsufficientStockError(AppException):
    """Stock level too low for the requested operation (400)."""

    status_code = 400
    error_code = "INSUFFICIENT_STOCK"


class DuplicateError(AppException):
    """Attempting to create a resource that already exists (409)."""

    status_code = 409
    error_code = "DUPLICATE"


class InvalidStateError(AppException):
    """Operation not allowed in the current state (400)."""

    status_code = 400
    error_code = "INVALID_STATE"

    def __init__(self, message: str = "Operation not allowed in current state"):
        super().__init__(message)


class AuthenticationError(AppException):
    """Missing or invalid credentials (401)."""

    status_code = 401
    error_code = "AUTHENTICATION_ERROR"

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class AuthorizationError(AppException):
    """Authenticated but insufficient permissions (403)."""

    status_code = 403
    error_code = "AUTHORIZATION_ERROR"

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message)


class DatabaseError(AppException):
    """Database operation failed (500). Sanitizes error details to prevent info leakage to clients."""

    status_code = 500
    error_code = "DATABASE_ERROR"

    def __init__(self, message: str = "A database error occurred", orig_cause: Exception = None):
        self.internal_detail = message
        if orig_cause:
            self.internal_detail = f"{message} | Cause: {orig_cause}"

        # Strip raw SQL / DB driver error text after colon if present
        client_message = message
        if ":" in message:
            client_message = message.split(":", 1)[0].strip()

        super().__init__(client_message)
