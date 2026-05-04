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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger("smart_inventory.db")

# ── Validate DATABASE_URL ─────────────────────────────────────────────────

if not settings.DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is REQUIRED. "
        "Set it to your database connection string. "
        "Examples: postgresql://user:pass@host/db or sqlite:///./database.db"
    )

DATABASE_URL = settings.DATABASE_URL

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
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a database session — automatically closed after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
