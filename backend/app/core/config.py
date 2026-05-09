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

    # ─── Notifications ────────────────────────────────────────────
    at_username: str = "sandbox"
    at_api_key: str = "dev-only-at-key"
    at_sender_id: str = "LANDLOADS"
    at_base_url: str = "https://api.sandbox.africastalking.com/version1"
    resend_api_key: str = "dev-only-resend-key"
    resend_base_url: str = "https://api.resend.com"
    email_from: str = "no-reply@landloads.co.ke"
    notifications_enabled: bool = False  # flip in staging/prod

    # ─── M-Pesa Daraja ────────────────────────────────────────────
    mpesa_env: Literal["sandbox", "production"] = "sandbox"
    mpesa_consumer_key: str = "dev-consumer-key"
    mpesa_consumer_secret: str = "dev-consumer-secret"
    mpesa_business_short_code: str = "174379"  # sandbox default
    mpesa_passkey: str = (
        "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
    )
    mpesa_paybill: str = "174379"
    mpesa_callback_secret: str = "dev-callback-secret-rotate-monthly"
    mpesa_callback_base_url: str = "https://localhost"  # set to public URL in prod
    mpesa_initiator_name: str = "testapi"
    mpesa_initiator_password: str = "Safaricom999!*!"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency."""
    return Settings()
