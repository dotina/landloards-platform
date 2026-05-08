"""Liveness and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/healthz", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def healthz() -> HealthResponse:
    """Liveness probe: returns 200 as long as the process can serve requests.

    Does NOT check downstream dependencies — see /readyz for that.
    """
    return HealthResponse(status="ok", version=APP_VERSION)
