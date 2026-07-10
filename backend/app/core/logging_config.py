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
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ── Log file location ─────────────────────────────────────────────────────
# Resolves to  <project_root>/logs/app.log
# core(0) → app(1) → backend(2) → InvIQ project root(3)
_LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
_LOG_FILE = _LOG_DIR / "app.log"

# Max 10 MB per file, keep last 5 rotated files  →  up to 50 MB on disk
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5


def setup_logging(environment: str = "development"):
    """Configure root + app logger with structured format.

    Two handlers are registered:
    - StreamHandler  (stdout) — UTF-8 safe, level follows env (DEBUG / INFO)
    - RotatingFileHandler (logs/app.log) — always INFO+, UTF-8, 10 MB × 5

    Forces UTF-8 encoding on the StreamHandler so that Unicode characters
    (arrows, emoji, etc.) in log messages do not cause UnicodeEncodeError
    on Windows, whose default console code page (cp1252) cannot encode them.
    """

    log_level = logging.DEBUG if environment == "development" else logging.INFO

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=date_fmt)

    # ── Stdout handler (UTF-8 safe) ───────────────────────────────────────
    try:
        utf8_stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
        stream_handler = logging.StreamHandler(stream=utf8_stdout)
    except AttributeError:
        # sys.stdout has no .buffer (e.g. inside pytest capsys) — fall back safely.
        stream_handler = logging.StreamHandler(stream=sys.stdout)

    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)

    # ── Rotating file handler (logs/app.log) ──────────────────────────────
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)   # always INFO+ in the file
    except Exception as _fh_err:
        # If we can't create the log file (e.g. read-only fs in CI), just skip it.
        file_handler = None
        logging.warning("Could not create log file at %s: %s", _LOG_FILE, _fh_err)

    # ── Root logger ───────────────────────────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)
    if file_handler:
        root_logger.addHandler(file_handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    app_logger = logging.getLogger("smart_inventory")
    app_logger.setLevel(log_level)
    app_logger.info(
        "Logging initialised → level=%s, env=%s, file=%s",
        log_level,
        environment,
        _LOG_FILE if file_handler else "disabled",
    )
