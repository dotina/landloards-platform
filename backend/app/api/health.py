"""Liveness and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.logging import get_logger

router = APIRouter(tags=["health"])

log = get_logger("app.health")


class HealthResponse(BaseModel):
    status: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


async def check_database() -> bool:
    """Return True iff `SELECT 1` succeeds against Postgres."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("readiness_db_check_failed", error=str(exc))
        return False


async def check_redis() -> bool:
    """Return True iff Redis PING succeeds."""
    client: Redis | None = None
    try:
        client = Redis.from_url(get_settings().redis_url)
        return bool(await client.ping())
    except Exception as exc:  # noqa: BLE001
        log.warning("readiness_redis_check_failed", error=str(exc))
        return False
    finally:
        if client is not None:
            await client.aclose()


@router.get("/healthz", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def healthz() -> HealthResponse:
    """Liveness probe: 200 as long as the process can serve requests.

    Does NOT check downstream dependencies — see /readyz for that.
    """
    return HealthResponse(status="ok", version=__version__)


@router.get("/readyz", response_model=ReadinessResponse)
async def readyz(response: Response) -> ReadinessResponse:
    """Readiness probe: checks DB + Redis. 503 if any check fails."""
    db_ok = await check_database()
    redis_ok = await check_redis()
    checks = {
        "database": "ok" if db_ok else "fail",
        "redis": "ok" if redis_ok else "fail",
    }
    if not (db_ok and redis_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="degraded", checks=checks)
    return ReadinessResponse(status="ready", checks=checks)
