"""
Application configuration — backed by Pydantic Settings v2.

Resolution order for every field (highest priority first):
  1. Real environment variable (e.g. set by Docker / CI / shell)
  2. First .env file found on the search path (see _find_env_file below)
  3. Default value declared on the field

Multi-path .env discovery searches:
  a. Current working directory  (./.env)
  b. Project root               (backend/../.env)
  c. Backend root               (backend/.env)

Production safety validation runs automatically when Settings is
instantiated (via @model_validator) — NOT at bare import time, so
individual test modules that import helpers from sub-packages are
never affected.

Side-effect note: configure_langsmith() is intentionally NOT called
here.  Call it explicitly from the FastAPI lifespan (app/main.py)
so it only runs when the server actually starts.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("smart_inventory")

_INSECURE_SECRET = "your-super-secret-key-change-in-production"


# ---------------------------------------------------------------------------
# .env path discovery
# ---------------------------------------------------------------------------

def _find_env_file() -> Optional[str]:
    """Return the first existing .env path from the candidate list, or None."""
    candidates = [
        Path(".").resolve() / ".env",                                        # cwd
        Path(__file__).resolve().parent.parent.parent.parent / ".env",       # project root
        Path(__file__).resolve().parent.parent.parent / ".env",              # backend root
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


# ---------------------------------------------------------------------------
# Settings — Pydantic BaseSettings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),          # multi-path .env resolution
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",                     # silently skip unknown env vars
    )

    # ── Application ────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Smart Inventory Assistant"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api"

    # ── Database ───────────────────────────────────────────────────────
    DATABASE_URL: str = ""

    # ── Frontend / CORS ────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    # Comma-separated in .env; exposed as list via property below.
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:5174"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parsed CORS origins list — use this in middleware config."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── AI / LLM ───────────────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = None
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024

    # ── LangSmith (Observability) ──────────────────────────────────────
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "InvIQ"
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # ── Qdrant Cloud (Vector Store) ────────────────────────────────────
    QDRANT_ENABLED: bool = True
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "chat_memory"

    # ── Auth & Security ────────────────────────────────────────────────
    SECRET_KEY: str = _INSECURE_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Login Lockout ──────────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # ── Super Admin ────────────────────────────────────────────────────
    SUPER_ADMIN_EMAIL: str = "admin@example.com"

    # ── Admin Seed (first startup only) ───────────────────────────────
    ADMIN_EMAIL: str = "admin@inventory.local"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""
    ADMIN_FULL_NAME: str = "System Administrator"

    # ── Upstash Redis (Caching & Rate Limiting) ────────────────────────
    REDIS_URL: str = ""
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    REDIS_ENABLED: bool = True

    # ── Rate Limiting ──────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "5/minute"

    # ── SMTP (Email Alerts) ────────────────────────────────────────────
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "InvIQ Smart Inventory"

    # ── External APIs ──────────────────────────────────────────────────
    GOOGLE_OAUTH_VERIFY_URL: str = (
        "https://www.googleapis.com/oauth2/v3/userinfo"
    )
    SARVAM_API_KEY: str = ""

    # ── Derived helpers ────────────────────────────────────────────────

    @property
    def redis_storage_uri(self) -> str:
        """
        Build the slowapi rate-limiter storage URI.
        - testing  → always in-memory
        - REDIS_URL set → use it directly
        - Upstash REST creds → construct rediss:// URL
        - fallback → in-memory
        """
        if self.ENVIRONMENT == "testing":
            return "memory://"

        if self.REDIS_URL:
            return self.REDIS_URL

        if self.UPSTASH_REDIS_REST_URL and self.UPSTASH_REDIS_REST_TOKEN:
            try:
                host = (
                    self.UPSTASH_REDIS_REST_URL
                    .replace("https://", "")
                    .replace("http://", "")
                    .split("/")[0]
                    .split(":")[0]
                )
                # ssl_cert_reqs=none works around macOS system CA store gaps.
                return (
                    f"rediss://default:{self.UPSTASH_REDIS_REST_TOKEN}"
                    f"@{host}:6379?ssl_cert_reqs=none"
                )
            except Exception:
                pass

        return "memory://"

    # ── Production safety validation ───────────────────────────────────

    @model_validator(mode="after")
    def _validate_production(self) -> "Settings":
        """
        Runs automatically when Settings() is instantiated.
        Raises ValueError (preventing server startup) if any critical
        production secret is missing or insecure.
        Only logs warnings for development environments.
        """
        if self.ENVIRONMENT == "production":
            # Hard failures — server must not start
            if self.SECRET_KEY == _INSECURE_SECRET:
                raise ValueError(
                    "FATAL: SECRET_KEY is still the insecure default! "
                    "Generate a secure key with: openssl rand -hex 32"
                )
            required = {
                "DATABASE_URL": self.DATABASE_URL,
                "SECRET_KEY": self.SECRET_KEY,
            }
            missing = [k for k, v in required.items() if not v]
            if missing:
                raise ValueError(
                    "FATAL: Missing required environment variables for production: "
                    + ", ".join(missing)
                )

            # Soft warnings — server starts but operator should be aware
            if not self.GROQ_API_KEY:
                logger.warning("⚠️  GROQ_API_KEY not set — AI chatbot will be disabled")
            if not self.UPSTASH_REDIS_REST_URL or not self.UPSTASH_REDIS_REST_TOKEN:
                logger.warning(
                    "⚠️  Upstash Redis not configured — using in-memory fallback for caching"
                )
            if not self.ADMIN_PASSWORD:
                logger.warning(
                    "⚠️  ADMIN_PASSWORD is empty — set a strong password for production"
                )

            logger.info("✅ Production configuration validated successfully")

        elif self.SECRET_KEY == _INSECURE_SECRET:
            logger.warning(
                "SECRET_KEY is using the insecure default — "
                "acceptable for local dev only. "
                "Generate a secure key for production: openssl rand -hex 32"
            )

        return self


# ---------------------------------------------------------------------------
# Singleton — import this everywhere
# ---------------------------------------------------------------------------

settings = Settings()


# ---------------------------------------------------------------------------
# LangSmith helper — call from FastAPI lifespan, NOT at import time
# ---------------------------------------------------------------------------

def configure_langsmith() -> None:
    """
    Apply LangSmith / LangChain tracing env-vars.

    This function has OS-level side effects (mutates os.environ) so it must
    be called explicitly from app startup (lifespan), never at bare import time.
    """
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
        logger.info(
            "✅ LangSmith tracing enabled → project: %s", settings.LANGCHAIN_PROJECT
        )
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.info("LangSmith tracing disabled — LANGCHAIN_API_KEY not set")
