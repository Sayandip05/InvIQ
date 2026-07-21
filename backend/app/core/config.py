import os
import logging
from dotenv import load_dotenv

from pathlib import Path

# Try to find .env in multiple locations
# 1. Current directory (for running from project root)
# 2. Parent of backend folder (project root)
# 3. Backend folder itself
possible_env_paths = [
    Path(".").resolve() / ".env",  # Current directory
    Path(__file__).resolve().parent.parent.parent.parent / ".env",  # Project root (backend/../)
    Path(__file__).resolve().parent.parent.parent / ".env",  # Backend folder
]

env_loaded = False
for env_path in possible_env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        env_loaded = True
        break

if not env_loaded:
    # Try loading without explicit path (uses cwd)
    load_dotenv()

logger = logging.getLogger("smart_inventory")


class Settings:
    # ── Application ───────────────────────────────────────────────────
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    PROJECT_NAME = "Smart Inventory Assistant"
    VERSION = "2.0.0"
    API_V1_PREFIX = "/api"
    
    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL = os.getenv("DATABASE_URL", "")  # PostgreSQL (Supabase) — REQUIRED
    
    # ── Frontend ──────────────────────────────────────────────────────
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:5174",
    ).split(",")
    
    # ── AI / LLM ──────────────────────────────────────────────────────
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    
    # ── LangSmith (Observability) ─────────────────────────────────────
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "InvIQ")
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    
    # ── Qdrant Cloud (Vector Store for RAG) ──────────────────────────
    QDRANT_ENABLED = os.getenv("QDRANT_ENABLED", "true").lower() == "true"
    QDRANT_URL = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "chat_memory")

    # ── Auth & Security ───────────────────────────────────────────────
    # REQUIRED: Generate a secure key with: openssl rand -hex 32
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ── Login Lockout ─────────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

    # ── Super Admin (platform owner) ────────────────────────────────
    SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")

    # ── Admin Seed (first startup only) ───────────────────────────────
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@inventory.local")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_FULL_NAME = os.getenv("ADMIN_FULL_NAME", "System Administrator")

    # ── Upstash Redis (Caching) ───────────────────────────────────────
    REDIS_URL = os.getenv("REDIS_URL", "")
    UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
    UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    @property
    def redis_storage_uri(self) -> str:
        """
        Build the storage URI for rate-limiting.
        If ENVIRONMENT is "testing", always return "memory://" to isolate tests.
        If REDIS_URL is explicitly set, use it.
        Otherwise, auto-construct the standard TCP/TLS Redis URL from Upstash REST credentials.
        Falls back to 'memory://' if no credentials are configured.
        """
        if self.ENVIRONMENT == "testing":
            return "memory://"

        if self.REDIS_URL:
            return self.REDIS_URL

        # Auto-construct from Upstash credentials if present
        if self.UPSTASH_REDIS_REST_URL and self.UPSTASH_REDIS_REST_TOKEN:
            try:
                # Strip https:// and trailing slashes/paths
                host = self.UPSTASH_REDIS_REST_URL.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
                # Upstash standard Redis uses TLS (rediss://) on port 6379.
                # ssl_cert_reqs=none skips cert verification on macOS local dev
                # (Python's SSL store isn't linked to the system keychain there).
                # In production Linux containers CA certs are present so this is harmless.
                return f"rediss://default:{self.UPSTASH_REDIS_REST_TOKEN}@{host}:6379?ssl_cert_reqs=none"
            except Exception:
                pass

        return "memory://"

    # ── Rate Limiting ─────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")
    
    # ── SMTP (Email) ──────────────────────────────────────────────────
    SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "InvIQ Smart Inventory")
    
    # ── External APIs ─────────────────────────────────────────────────
    GOOGLE_OAUTH_VERIFY_URL = os.getenv(
        "GOOGLE_OAUTH_VERIFY_URL",
        "https://www.googleapis.com/oauth2/v3/userinfo"
    )
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")


settings = Settings()


# ── Production safety checks ──────────────────────────────────────────────
def _validate_production_config():
    """Fail loudly if critical secrets are using insecure defaults in production."""
    if settings.ENVIRONMENT == "production":
        # Check SECRET_KEY
        if settings.SECRET_KEY == "your-super-secret-key-change-in-production":
            raise ValueError(
                "FATAL: SECRET_KEY is still the insecure default! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        
        # Check ADMIN_PASSWORD
        if settings.ADMIN_PASSWORD == "":
            logger.warning(
                "⚠️  ADMIN_PASSWORD is empty. "
                "Set ADMIN_PASSWORD env var to a strong password for production."
            )
        
        # Validate required environment variables
        required_vars = {
            "DATABASE_URL": settings.DATABASE_URL,
            "SECRET_KEY": settings.SECRET_KEY,
        }
        
        missing = [k for k, v in required_vars.items() if not v or v == ""]
        if missing:
            raise ValueError(
                f"FATAL: Missing required environment variables for production: {', '.join(missing)}"
            )
        
        # Warn about optional but recommended vars
        if not settings.GROQ_API_KEY:
            logger.warning("⚠️  GROQ_API_KEY not set — AI chatbot will be disabled")
        
        if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
            logger.warning("⚠️  Upstash Redis not configured — using in-memory fallback for caching")
        
        logger.info("✅ Production configuration validated successfully")
        
    elif settings.SECRET_KEY == "your-super-secret-key-change-in-production":
        logger.warning(
            "SECRET_KEY is using the insecure default — acceptable for local dev only. "
            "Generate a secure key for production: openssl rand -hex 32"
        )


_validate_production_config()


def configure_langsmith():
    """Configure LangSmith observability using LANGCHAIN_* environment variables."""
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


configure_langsmith()
