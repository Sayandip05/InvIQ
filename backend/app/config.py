import os
import logging
from dotenv import load_dotenv

from pathlib import Path

# Get the project root directory (current file is in backend/app/config.py)
# Root is backend/../ -> ../
root_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("smart_inventory")

class Settings:
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "../database/smart_inventory.db")
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
    
    # LangSmith (observability & tracing)
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "smart-inventory-assistant")
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # CORS
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:5173,http://localhost:5174"
    ).split(",")
    
    # API Settings
    API_V1_PREFIX = "/api"
    PROJECT_NAME = "Smart Inventory Assistant"
    VERSION = "2.0.0"

settings = Settings()


def configure_langsmith():
    """Auto-enable LangSmith tracing when API key is available."""
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        logger.info("LangSmith tracing enabled → project: %s", settings.LANGCHAIN_PROJECT)
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


# Auto-configure on import
configure_langsmith()
