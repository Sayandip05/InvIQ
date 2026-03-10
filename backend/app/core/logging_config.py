"""
Structured logging configuration.

Call setup_logging() once at app startup (from main.py).
All modules should use:
    import logging
    logger = logging.getLogger("smart_inventory")
"""

import logging
import sys


def setup_logging(environment: str = "development"):
    """Configure root + app logger with structured format."""

    log_level = logging.DEBUG if environment == "development" else logging.INFO

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=fmt,
        datefmt=date_fmt,
        stream=sys.stdout,
        force=True,  # override any existing config
    )

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    app_logger = logging.getLogger("smart_inventory")
    app_logger.setLevel(log_level)
    app_logger.info("Logging initialised — level=%s, env=%s", log_level, environment)
