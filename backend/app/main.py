"""
FastAPI application entry point.

Configures middleware, routes, exception handlers, and lifecycle events.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.routes import analytics, chat, inventory, requisition, auth, admin
from app.api.routes import vendor as vendor_routes
from app.api.routes import data_import as data_import_routes
from app.api.routes import billing as billing_routes
from app.api.routes.websocket import router as ws_router
from app.api.graphql.schema import graphql_router
from app.core.config import settings, configure_langsmith
from app.infrastructure.database.connection import Base, engine
from app.core.logging_config import setup_logging
from app.core.error_handlers import register_exception_handlers
from app.core.middleware.request_logger import RequestLoggerMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.security import hash_password

from app.core.rate_limiter import limiter, rate_limit_handler
from app.infrastructure.database.models import User, AuditLog  # noqa: F401
from app.infrastructure.cache.redis_client import get_redis, close_redis

setup_logging(settings.ENVIRONMENT)
logger = logging.getLogger("smart_inventory")


def seed_admin_user():
    """
    Seed initial tenant admin user ONLY in development/testing environments.
    Admin provisioning is performed securely with strong credentials.
    """
    if settings.ENVIRONMENT not in ["development", "testing"]:
        return

    try:
        from app.infrastructure.database.connection import SessionLocal
        from app.infrastructure.database.models import User, Organization

        with SessionLocal() as db:
            # Seed Admin for local development/testing only if configured
            existing_admin = db.query(User).filter(User.role == "admin").first()
            if not existing_admin and settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
                org = db.query(Organization).first()
                if not org:
                    org = Organization(
                        name="Apex Care Pharmacy",
                        slug="apex-care",
                        plan="single_pharmacy",
                        is_active=True,
                    )
                    db.add(org)
                    db.commit()
                    db.refresh(org)

                admin_user = User(
                    email=settings.ADMIN_EMAIL,
                    username=settings.ADMIN_USERNAME or "admin",
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    full_name=settings.ADMIN_FULL_NAME or "Development Admin",
                    role="admin",
                    is_active=True,
                    is_verified=True,
                    org_id=org.id,
                )
                db.add(admin_user)
                db.commit()
                logger.info(
                    "Development admin user created (email: %s)", settings.ADMIN_EMAIL
                )
    except Exception as e:
        logger.warning("Could not seed development admin user: %s", str(e))




# ── Lifespan (Graceful Startup + Shutdown) ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle."""
    # ── Startup ──
    configure_langsmith()          # apply LangSmith env-vars (no import-time side effects)

    # In production, schemas are managed exclusively via Alembic migrations.
    # create_all() is only run in development/testing for rapid local iteration.
    if settings.ENVIRONMENT != "production":
        Base.metadata.create_all(bind=engine)

    seed_admin_user()
    get_redis()  # Initialize Redis connection (logs status)

    # Start WebSocket Redis pub/sub subscriber background task
    import asyncio
    from app.api.routes.websocket import start_redis_subscriber
    subscriber_task = asyncio.create_task(start_redis_subscriber())

    logger.info(
        "[START] %s v%s — %d route groups loaded (+ GraphQL at /graphql/analytics)",
        settings.PROJECT_NAME,
        settings.VERSION,
        7,
    )
    yield
    # ── Shutdown ──
    subscriber_task.cancel()
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
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# ── Middleware ─────────────────────────────────────────────────────────────
# NOTE: Starlette add_middleware() wraps in LIFO order — the middleware added
# LAST runs FIRST. Order here: RequestLoggerMiddleware (runs 1st) → CORSMiddleware (runs 2nd).
# RequestLoggerMiddleware must run first so it can pass WebSocket upgrade
# connections straight through (scope["type"] == "websocket") before
# CORSMiddleware processes them.
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggerMiddleware)


# ── Exception Handlers ────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routes ─────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory.router, prefix=settings.API_V1_PREFIX)
app.include_router(requisition.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(vendor_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(data_import_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(billing_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws_router)

# ── GraphQL (analytics reads only — REST handles all mutations) ────────────
app.include_router(graphql_router, prefix="/graphql/analytics")


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
    from fastapi.responses import JSONResponse

    redis_ok = is_redis_available()
    status = "healthy" if redis_ok else "degraded"
    http_status = 200 if redis_ok else 503

    return JSONResponse(
        status_code=http_status,
        content={
            "status": status,
            "version": settings.VERSION,
            "database": "connected",
            "redis": "connected" if redis_ok else "unavailable",
        },
    )


@app.get("/api/config/public")
def public_config():
    """Return non-sensitive config values that the frontend needs at boot time.

    Only the Google Client ID (public by nature) is exposed here.
    Client Secrets are NEVER returned.
    """
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID or "",
    }

