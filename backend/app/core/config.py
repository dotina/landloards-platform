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

    # ─── Auth ─────────────────────────────────────────────────────
    jwt_secret: str = Field(
        default="dev-only-jwt-secret-change-in-prod-min-32-chars-long",
        description="HMAC-SHA256 key for access + refresh JWTs",
    )
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30
    invite_token_ttl_days: int = 7
    otp_ttl_minutes: int = 10
    pii_encryption_key: str = Field(
        default="dev-only-pii-key-change-in-prod-32-chars",
        description="pgcrypto pgp_sym_encrypt key for ID number / KRA PIN",
    )

    # ─── Cookie / CSRF ────────────────────────────────────────────
    cookie_secure: bool = False  # True in prod (HTTPS-only)
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency."""
    return Settings()
