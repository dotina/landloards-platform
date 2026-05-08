"""Tests for /healthz and /readyz endpoints."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch):
    """Provide a fully-configured FastAPI app for tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")
    monkeypatch.setenv("MINIO_ENDPOINT", "h:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "k")
    monkeypatch.setenv("MINIO_SECRET_KEY", "s")
    monkeypatch.setenv("MINIO_BUCKET", "b")
    from app.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_healthz_returns_ok(app) -> None:
    """/healthz must return 200 and a status payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
