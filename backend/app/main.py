import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, chat, inventory, requisition
from app.config import settings
from app.database.connection import Base, engine
from app.core.logging_config import setup_logging
from app.core.error_handlers import register_exception_handlers
from app.middleware.request_logger import RequestLoggerMiddleware

# ─── Initialise logging FIRST ───
setup_logging(settings.ENVIRONMENT)
logger = logging.getLogger("smart_inventory")

# ─── Create app ───
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered inventory management for healthcare supply chains",
)

# Ensure core tables exist even when starting with an empty database.
Base.metadata.create_all(bind=engine)

# ─── Middleware (order matters: outermost first) ───
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global error handlers ───
register_exception_handlers(app)

# ─── Routes ───
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory.router, prefix=settings.API_V1_PREFIX)
app.include_router(requisition.router, prefix=settings.API_V1_PREFIX)

logger.info(
    "🚀 %s v%s started — %d route groups loaded",
    settings.PROJECT_NAME,
    settings.VERSION,
    4,
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
