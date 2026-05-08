"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    All values come from environment variables. See `.env.example` at the
    repo root for the canonical list.
    """

    model_config = SettingsConfigDict(
        env_file=None,                # don't auto-load; Docker/CI provide env
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: str = Field(..., description="SQLAlchemy async DB URL")
    redis_url: str = Field(..., description="Redis URL for cache and arq queue")

    minio_endpoint: str = Field(..., description="host:port of MinIO")
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_use_ssl: bool = False

    sentry_dsn: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency."""
    return Settings()
