"""Tests for the Settings class."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_settings_loads_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings populates from env vars (overrides conftest defaults)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")

    from app.core.config import Settings
    settings = Settings()

    assert settings.database_url == "postgresql+asyncpg://u:p@h:5432/d"
    assert settings.redis_url == "redis://h:6379/0"
    assert settings.app_env == "development"  # default
    assert settings.log_level == "INFO"        # default


def test_settings_rejects_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing DATABASE_URL must fail validation."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.core.config import Settings
    with pytest.raises(ValidationError):
        Settings()
