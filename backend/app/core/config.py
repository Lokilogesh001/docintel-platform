import os
from pathlib import Path
from typing import Optional

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"

# Load local .env manually or with pydantic-settings/os
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key not in os.environ:
                    os.environ[key] = val

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "DocIntel-Platform")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # LLM Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or None
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY") or None
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

    # OCR Settings
    OCR_SPACE_API_KEY: str = os.getenv("OCR_SPACE_API_KEY", "helloworld")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'docintel.db'}")

    # Processing limits & validation rules
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))
    MAX_PAGE_COUNT: int = int(os.getenv("MAX_PAGE_COUNT", "3"))
    FINANCIAL_TOLERANCE: float = float(os.getenv("FINANCIAL_TOLERANCE", "0.05"))

    # Supported Document Types
    SUPPORTED_DOCUMENT_TYPES = [
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement"
    ]

    # Supported File Formats
    SUPPORTED_MIME_TYPES = {
        "application/pdf": "PDF",
        "image/jpeg": "JPG",
        "image/png": "PNG"
    }
    SUPPORTED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"]

settings = Settings()
