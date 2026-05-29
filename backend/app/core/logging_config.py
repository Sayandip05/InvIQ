"""
Structured logging configuration.

Call setup_logging() once at app startup (from main.py).
All modules should use:
    import logging
    logger = logging.getLogger("smart_inventory")
"""

import logging
import sys
import io


def setup_logging(environment: str = "development"):
    """Configure root + app logger with structured format.

    Forces UTF-8 encoding on the StreamHandler so that Unicode characters
    (arrows, emoji, etc.) in log messages do not cause UnicodeEncodeError
    on Windows, whose default console code page (cp1252) cannot encode them.
    """

    log_level = logging.DEBUG if environment == "development" else logging.INFO

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=date_fmt)

    # Build a UTF-8 StreamHandler that survives Windows cp1252 consoles.
    # TextIOWrapper re-wraps the raw binary stdout buffer with explicit UTF-8
    # so emoji / arrow characters never trigger a codec error.
    try:
        utf8_stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
        handler = logging.StreamHandler(stream=utf8_stdout)
    except AttributeError:
        # sys.stdout has no .buffer (e.g. inside pytest capsys) — fall back safely.
        handler = logging.StreamHandler(stream=sys.stdout)

    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Replace any existing handlers to avoid duplicate output.
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    app_logger = logging.getLogger("smart_inventory")
    app_logger.setLevel(log_level)
    app_logger.info("Logging initialised -> level=%s, env=%s", log_level, environment)
