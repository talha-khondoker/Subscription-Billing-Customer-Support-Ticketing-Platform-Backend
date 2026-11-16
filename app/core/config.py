# ----------------------------------------------------------------------
# app/core/config.py
# Owner:   Shared (Member 1 owns; ask before changing)
# Purpose: Settings read from environment variables / .env.
# ----------------------------------------------------------------------
# TODO:
#   - ENV, DATABASE_URL, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
#   - RETRY_SCHEDULE_DAYS (default 1,3,5), MAX_RETRY_ATTEMPTS (default 3)
#   - SCHEDULER_ENABLED, CORS_ORIGINS, DEFAULT_TAX_PERCENT
#   - expose one settings object imported everywhere


"""Application settings. Values come from environment variables or a .env file."""
import os

try:  # python-dotenv is optional; it only loads the .env file when installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Settings:
    ENV: str = os.getenv("ENV", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./subflow.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    RETRY_SCHEDULE_DAYS: list[int] = [int(d) for d in os.getenv("RETRY_SCHEDULE_DAYS", "1,3,5").split(",")]
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    DEFAULT_TAX_PERCENT: float = float(os.getenv("DEFAULT_TAX_PERCENT", "0"))


settings = Settings()

