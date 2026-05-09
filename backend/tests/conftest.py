"""Shared pytest fixtures."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

# Safe default env values so modules that call get_settings() at import time
# (e.g. app.main, app.jobs.worker) can be imported during test collection.
# Individual tests that need different values override via their own monkeypatch.
_DEFAULT_ENV = {
    "APP_ENV": "development",
    "LOG_LEVEL": "INFO",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "MINIO_ENDPOINT": "localhost:9000",
    "MINIO_ACCESS_KEY": "test",
    "MINIO_SECRET_KEY": "test",
    "MINIO_BUCKET": "test",
    "MINIO_USE_SSL": "false",
    "JWT_SECRET": "test-jwt-secret-please-do-not-use-in-prod-32+chars",
    "PII_ENCRYPTION_KEY": "test-pii-key-32-chars-or-longer",
    "COOKIE_SECURE": "false",
    "COOKIE_SAMESITE": "lax",
}


@pytest.fixture(autouse=True)
def _default_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Set default env vars before each test and clear the Settings cache.

    Tests that test "missing required env" use monkeypatch.delenv explicitly.
    Tests that need different values override via monkeypatch.setenv.
    """
    for key, value in _DEFAULT_ENV.items():
        monkeypatch.setenv(key, value)

    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
