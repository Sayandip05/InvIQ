import os
import logging
from dotenv import load_dotenv

from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("smart_inventory")


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "")  # PostgreSQL string (required)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "smart-inventory-assistant")
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:5174",
    ).split(",")
    API_V1_PREFIX = "/api"
    PROJECT_NAME = "Smart Inventory Assistant"
    VERSION = "2.0.0"

    # ── Auth & Security ───────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ── Login Lockout ─────────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

    # ── Admin Seed (first startup) ────────────────────────────────────
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@inventory.local")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_FULL_NAME = os.getenv("ADMIN_FULL_NAME", "System Administrator")

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL = os.getenv("REDIS_URL", "")  # e.g. redis://localhost:6379 or Upstash URL

    # ── Rate Limiting ─────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")


settings = Settings()


def configure_langsmith():
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        logger.info(
            "LangSmith tracing enabled → project: %s", settings.LANGCHAIN_PROJECT
        )
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


configure_langsmith()
