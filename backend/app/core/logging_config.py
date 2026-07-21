"""
Structured logging configuration for InvIQ.

Usage
-----
Call ``setup_logging()`` exactly once at app startup (main.py).
Every module should obtain its logger with::

    import logging
    logger = logging.getLogger("smart_inventory.<module>")

Log files (local development only)
------------------------------------
All files live in  <project_root>/logs/   (one level above /backend)

    logs/
    ├── app.log       – everything INFO+ (general, rotated 10 MB × 5)
    ├── access.log    – HTTP request/response lines (uvicorn.access)
    ├── error.log     – WARNING+ only across all loggers
    └── agent.log     – AI agent + vector-store interactions (DEBUG+)

Production
----------
Only a structured JSON StreamHandler (stdout) is attached.
Grafana / Prometheus / Loki picks these up from container stdout.
"""

from __future__ import annotations

import io
import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────────────
# core(0) → app(1) → backend(2) → InvIQ project root(3)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOG_DIR = _PROJECT_ROOT / "logs"

# Individual log files
_APP_LOG     = _LOG_DIR / "app.log"      # all INFO+
_ACCESS_LOG  = _LOG_DIR / "access.log"   # uvicorn HTTP access
_ERROR_LOG   = _LOG_DIR / "error.log"    # WARNING+ across all loggers
_AGENT_LOG   = _LOG_DIR / "agent.log"    # AI agent + Qdrant interactions

# Rotation: 10 MB per file, keep last 5  →  max 50 MB per file set
_MAX_BYTES    = 10 * 1024 * 1024
_BACKUP_COUNT = 5


# ── Formatters ────────────────────────────────────────────────────────────────

_PLAIN_FMT  = "%(asctime)s | %(levelname)-8s | %(name)-32s | %(message)s"
_DATE_FMT   = "%Y-%m-%d %H:%M:%S"
_plain_formatter = logging.Formatter(fmt=_PLAIN_FMT, datefmt=_DATE_FMT)


class _JsonFormatter(logging.Formatter):
    """
    Emits one JSON object per log record on a single line.
    Consumed by Grafana Loki / any log shipper in production.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict = {
            "ts":      datetime.now(tz=timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rotating(path: Path, level: int) -> logging.handlers.RotatingFileHandler | None:
    """Create a RotatingFileHandler; return None if the filesystem is read-only."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(_plain_formatter)
        handler.setLevel(level)
        return handler
    except Exception as exc:
        logging.warning("Could not create log file %s: %s", path, exc)
        return None


def _utf8_stream_handler(level: int, formatter: logging.Formatter) -> logging.StreamHandler:
    """Return a UTF-8-safe StreamHandler (handles Windows cp1252 consoles)."""
    try:
        stream = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
    except AttributeError:
        # pytest capsys / environments without .buffer
        stream = sys.stdout  # type: ignore[assignment]
    handler = logging.StreamHandler(stream=stream)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


# ── Public API ────────────────────────────────────────────────────────────────

def setup_logging(environment: str = "development") -> None:
    """
    Configure the root logger + per-logger overrides.

    Local development
    -----------------
    * stdout     – human-readable, DEBUG-level colour-friendly plain text
    * app.log    – INFO+  (general application events)
    * access.log – INFO+  (HTTP access log from uvicorn.access)
    * error.log  – WARNING+ (all errors in one place for quick triage)
    * agent.log  – DEBUG+  (LLM / Qdrant / vector-store trace)

    Production
    ----------
    * stdout only – structured JSON (one record per line) for Grafana Loki.
    """
    is_dev  = environment == "development"
    is_test = environment == "testing"

    base_level = logging.DEBUG if is_dev else logging.INFO

    # ── Root logger ───────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(base_level)

    if is_test:
        # Tests only need a minimal console handler to avoid noise
        root.addHandler(_utf8_stream_handler(logging.WARNING, _plain_formatter))
        return

    if is_dev:
        # ① Console (plain, DEBUG)
        root.addHandler(_utf8_stream_handler(logging.DEBUG, _plain_formatter))

        # ② app.log — general INFO+
        if h := _rotating(_APP_LOG, logging.INFO):
            root.addHandler(h)

        # ③ error.log — WARNING+ across all loggers
        if h := _rotating(_ERROR_LOG, logging.WARNING):
            root.addHandler(h)

    else:
        # Production: JSON to stdout only
        root.addHandler(_utf8_stream_handler(logging.INFO, _JsonFormatter()))

    # ── Per-logger customisation ───────────────────────────────────────────────

    # uvicorn HTTP access → access.log (dev only)
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.propagate = False          # don't double-write to root
    if is_dev:
        access_logger.setLevel(logging.INFO)
        if h := _rotating(_ACCESS_LOG, logging.INFO):
            access_logger.addHandler(h)
        # Also mirror to console so dev sees requests live
        access_logger.addHandler(_utf8_stream_handler(logging.INFO, _plain_formatter))
    else:
        access_logger.setLevel(logging.INFO)
        access_logger.addHandler(_utf8_stream_handler(logging.INFO, _JsonFormatter()))

    # AI agent + vector store → agent.log (dev only, DEBUG)
    for _agent_logger_name in (
        "smart_inventory.agent",
        "smart_inventory.vector_store",
        "smart_inventory.graphql",
    ):
        lg = logging.getLogger(_agent_logger_name)
        if is_dev:
            lg.propagate = True              # still reaches root (app.log + console)
            if h := _rotating(_AGENT_LOG, logging.DEBUG):
                lg.addHandler(h)

    # Silence noisy third-party loggers
    for noisy in (
        "sqlalchemy.engine",
        "qdrant_client",
        "httpx",
        "httpcore",
        "sentence_transformers",
        "transformers",
        "torch",
        "PIL",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Confirm boot
    app_logger = logging.getLogger("smart_inventory")
    app_logger.setLevel(base_level)
    app_logger.info(
        "Logging ready | env=%s | log_dir=%s",
        environment,
        str(_LOG_DIR) if is_dev else "stdout-only (JSON)",
    )
