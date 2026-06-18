"""
LTIA Radar — Application Configuration
Uses pydantic-settings to load from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://mongodb:27017")
    mongodb_database: str = Field(default="ltia_radar")

    # Google Gemini AI
    gemini_api_key: str = Field(default="")

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # Backend
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://frontend:3000"]
    )

    # Crawler
    crawler_interval_minutes: int = Field(default=60)
    crawler_max_concurrent: int = Field(default=5)
    llm_rate_limit_per_minute: int = Field(default=10)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
