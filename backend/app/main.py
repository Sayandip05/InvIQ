import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, chat, inventory, requisition, auth
from app.core.config import settings
from app.infrastructure.database.connection import Base, engine
from app.core.logging_config import setup_logging
from app.core.error_handlers import register_exception_handlers
from app.core.middleware.request_logger import RequestLoggerMiddleware
from app.core.security import hash_password
from app.infrastructure.database.models import User
from sqlalchemy.orm import Session

setup_logging(settings.ENVIRONMENT)
logger = logging.getLogger("smart_inventory")


def seed_admin_user():
    try:
        from app.infrastructure.database.connection import SessionLocal

        db = SessionLocal()
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if not existing_admin:
            admin = User(
                email="admin@inventory.local",
                username="admin",
                hashed_password=hash_password("admin123"),
                full_name="System Administrator",
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            db.commit()
            logger.info(
                "Default admin user created (username: admin, password: admin123)"
            )
        else:
            logger.info("Admin user already exists")
        db.close()
    except Exception as e:
        logger.warning("Could not seed admin user: %s", str(e))


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered inventory management for healthcare supply chains",
)

Base.metadata.create_all(bind=engine)

app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory.router, prefix=settings.API_V1_PREFIX)
app.include_router(requisition.router, prefix=settings.API_V1_PREFIX)

seed_admin_user()

logger.info(
    "🚀 %s v%s started — %d route groups loaded",
    settings.PROJECT_NAME,
    settings.VERSION,
    5,
)


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
    return {
        "status": "healthy",
        "database": "connected",
        "endpoints": [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/auth/me",
            "/api/analytics/heatmap",
            "/api/analytics/alerts",
            "/api/analytics/summary",
            "/api/chat/query",
            "/api/chat/suggestions",
            "/api/chat/history/{conversation_id}",
            "/api/inventory/locations",
            "/api/inventory/items",
            "/api/inventory/location/{location_id}/items",
            "/api/inventory/stock/{location_id}/{item_id}",
            "/api/inventory/reset-data",
            "/api/inventory/transaction",
            "/api/inventory/bulk-transaction",
            "/api/requisition/create",
            "/api/requisition/list",
            "/api/requisition/stats",
            "/api/requisition/{id}/approve",
            "/api/requisition/{id}/reject",
        ],
    }
