"""Liveness and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/healthz", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def healthz() -> HealthResponse:
    """Liveness probe: returns 200 as long as the process can serve requests.

    Does NOT check downstream dependencies — see /readyz for that.
    """
    return HealthResponse(status="ok", version=__version__)
