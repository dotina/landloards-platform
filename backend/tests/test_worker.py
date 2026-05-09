"""Tests for the arq WorkerSettings."""
from __future__ import annotations

import pytest
from arq.connections import RedisSettings


def test_worker_settings_lists_functions() -> None:
    """WorkerSettings.functions must be a list (empty is fine for now)."""
    from app.jobs.worker import WorkerSettings
    assert isinstance(WorkerSettings.functions, list)


def test_worker_settings_redis_settings_is_redis_settings() -> None:
    """WorkerSettings.redis_settings must resolve to an arq RedisSettings."""
    from app.jobs.worker import WorkerSettings
    assert isinstance(WorkerSettings.redis_settings, RedisSettings)


def test_worker_settings_redis_settings_reflects_current_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lazy descriptor must pick up the current REDIS_URL on each access."""
    monkeypatch.setenv("REDIS_URL", "redis://myredis:6379/2")
    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.jobs.worker import WorkerSettings
    rs = WorkerSettings.redis_settings
    assert rs.host == "myredis"
    assert rs.port == 6379
    assert rs.database == 2
