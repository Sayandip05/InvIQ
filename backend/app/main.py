"""
FastAPI application entry point.

Configures middleware, routes, exception handlers, and lifecycle events.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import analytics, chat, inventory, requisition, auth, admin
from app.core.config import settings
from app.infrastructure.database.connection import Base, engine
from app.core.logging_config import setup_logging
from app.core.error_handlers import register_exception_handlers
from app.core.middleware.request_logger import RequestLoggerMiddleware
from app.core.security import hash_password
from app.core.rate_limiter import limiter
from app.infrastructure.database.models import User, AuditLog  # noqa: F401
from app.infrastructure.cache.redis_client import get_redis, close_redis

setup_logging(settings.ENVIRONMENT)
logger = logging.getLogger("smart_inventory")


def seed_admin_user():
    try:
        from app.infrastructure.database.connection import SessionLocal

        db = SessionLocal()
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if not existing_admin:
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                full_name=settings.ADMIN_FULL_NAME,
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            db.commit()
            logger.info(
                "Default admin user created (username: %s)", settings.ADMIN_USERNAME
            )
        else:
            logger.info("Admin user already exists")
        db.close()
    except Exception as e:
        logger.warning("Could not seed admin user: %s", str(e))


# ── Lifespan (Graceful Startup + Shutdown) ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle."""
    # ── Startup ──
    Base.metadata.create_all(bind=engine)
    seed_admin_user()
    get_redis()  # Initialize Redis connection (logs status)
    logger.info(
        "[START] %s v%s — %d route groups loaded",
        settings.PROJECT_NAME,
        settings.VERSION,
        6,
    )
    yield
    # ── Shutdown ──
    close_redis()
    engine.dispose()
    logger.info("[STOP] %s shutdown complete", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered inventory management for healthcare supply chains",
    lifespan=lifespan,
)

# ── Rate Limiter ───────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ─────────────────────────────────────────────────────────────
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routes ─────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory.router, prefix=settings.API_V1_PREFIX)
app.include_router(requisition.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "message": "Smart Inventory Assistant API",
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    from app.infrastructure.cache.redis_client import is_redis_available

    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected" if is_redis_available() else "unavailable",
    }
