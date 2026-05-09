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
