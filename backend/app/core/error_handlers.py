"""
Global exception handlers registered on the FastAPI app.

These ensure every error returns a consistent JSON shape:
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Location with id '99' not found"
    }
}
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import AppException

logger = logging.getLogger("smart_inventory")


def register_exception_handlers(app: FastAPI):
    """Call this once from main.py to wire up all handlers."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException):
        logger.warning(
            "AppException: %s [%s] — %s",
            exc.error_code,
            exc.status_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ):
        errors = exc.errors()
        details = "; ".join(
            f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in errors
        )
        logger.warning("Validation error: %s", details)
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": details,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal server error occurred",
                },
            },
        )
