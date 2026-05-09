"""Tests for /healthz and /readyz endpoints."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app() -> FastAPI:
    """Build a fresh FastAPI app per test.

    Env defaults are populated by the autouse fixture in conftest.py;
    individual tests may override via their own monkeypatch.
    """
    from app.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_healthz_returns_ok(app: FastAPI) -> None:
    """/healthz must return 200 and a status payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.asyncio
async def test_readyz_returns_ok_when_deps_healthy(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/readyz returns 200 when DB and Redis ping succeed."""
    from app.api import health as health_module

    async def _ok_db() -> bool:
        return True

    async def _ok_redis() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_database", _ok_db)
    monkeypatch.setattr(health_module, "check_redis", _ok_redis)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}


@pytest.mark.asyncio
async def test_readyz_returns_503_when_db_down(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/readyz returns 503 when DB ping fails."""
    from app.api import health as health_module

    async def _bad_db() -> bool:
        return False

    async def _ok_redis() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_database", _bad_db)
    monkeypatch.setattr(health_module, "check_redis", _ok_redis)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["checks"]["database"] == "fail"
    assert body["checks"]["redis"] == "ok"
