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

    # Crawler & LLM Rate Limits (Google AI Studio Free Tier conservative defaults per key/project)
    crawler_interval_minutes: int = Field(default=60)
    crawler_max_concurrent: int = Field(default=5)
    llm_rate_limit_per_minute: int = Field(default=5)
    llm_rpm_per_key: int = Field(default=5)       # Free tier Flash models typically allow 5-15 RPM
    llm_tpm_per_key: int = Field(default=200000)  # Free tier Flash models typically allow 250k TPM
    llm_rpd_per_key: int = Field(default=250)     # Free tier Flash models typically allow 250-1500 RPD
    llm_max_wait_seconds: float = Field(default=180.0)
    llm_batch_max_articles: int = Field(default=15)
    llm_batch_max_chars: int = Field(default=45000)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
