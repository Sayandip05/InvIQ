"""
Database connection — PostgreSQL (Supabase) or SQLite.

Layer: Infrastructure

DATABASE_URL is REQUIRED in all environments.
For production: Set it to your Supabase PostgreSQL connection string.
For development: SQLite is supported (e.g., sqlite:///./database.db)
"""

import logging
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

logger = logging.getLogger("smart_inventory.db")

# ── Validate DATABASE_URL ─────────────────────────────────────────────────

if not settings.DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is REQUIRED. "
        "Set it to your database connection string. "
        "Examples: postgresql://user:pass@host/db or sqlite:///./database.db"
    )

import re

def sanitize_db_url(url: str) -> str:
    """
    Sanitize database connection URL.
    Strips parameters like 'pgbouncer=true' which are Prisma-specific and
    rejected by PostgreSQL libpq / psycopg2.
    """
    if not url:
        return url
    cleaned = re.sub(r"([?&])pgbouncer=[^&#]*(&?)", lambda m: m.group(1) if m.group(2) else "", url)
    cleaned = re.sub(r"[?&]$", "", cleaned)
    cleaned = re.sub(r"\?&", "?", cleaned)
    return cleaned

DATABASE_URL = sanitize_db_url(settings.DATABASE_URL)

logger.info("Database: PostgreSQL")

# ── Engine — connection pool optimized for production ─────────────────────

is_sqlite = DATABASE_URL.startswith("sqlite")


def create_engine_with_retry(url: str, max_retries: int = 3, **kwargs):
    """
    Create SQLAlchemy engine with retry logic for transient connection failures.
    
    Args:
        url: Database connection string
        max_retries: Maximum number of connection attempts
        **kwargs: Additional arguments passed to create_engine
    
    Returns:
        SQLAlchemy engine instance
    
    Raises:
        Exception: If all retry attempts fail
    """
    for attempt in range(1, max_retries + 1):
        try:
            engine = create_engine(url, **kwargs)
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("✅ Database connection established (attempt %d/%d)", attempt, max_retries)
            return engine
            
        except Exception as e:
            if attempt == max_retries:
                logger.error("❌ Database connection failed after %d attempts: %s", max_retries, e)
                raise
            
            wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
            logger.warning(
                "⚠️  Database connection attempt %d/%d failed: %s. Retrying in %ds...",
                attempt, max_retries, e, wait_time
            )
            time.sleep(wait_time)


if is_sqlite:
    engine = create_engine_with_retry(
        DATABASE_URL,
        max_retries=1,  # SQLite doesn't need retries
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine_with_retry(
        DATABASE_URL,
        max_retries=3,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0-style declarative base.

    All ORM models inherit from this class.  Using DeclarativeBase
    (sqlalchemy.orm) instead of the legacy declarative_base() from
    sqlalchemy.ext.declarative which was soft-deprecated in 1.4 and
    will be removed in SQLAlchemy 3.0.
    """
    pass


def get_db():
    """Yield a database session — automatically closed after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


import threading

# ── Query Performance Profiler ─────────────────────────────────────────────
_query_stats_lock = threading.Lock()
_query_history = []  # List of {"statement": str, "duration_ms": float}

from sqlalchemy import event

@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()

@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if hasattr(context, "_query_start_time"):
        duration_ms = (time.perf_counter() - context._query_start_time) * 1000
        with _query_stats_lock:
            if len(_query_history) > 10000:
                _query_history.pop(0)
            _query_history.append({
                "statement": statement.strip().replace("\n", " "),
                "duration_ms": duration_ms,
            })

def get_query_metrics():
    """Return a copy of the query timing history."""
    with _query_stats_lock:
        return list(_query_history)

def clear_query_metrics():
    """Clear the query timing history."""
    with _query_stats_lock:
        _query_history.clear()


from contextlib import contextmanager

@contextmanager
def get_db_context():
    """Context-manager version of get_db() for use outside FastAPI request scope."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()



