"""FastAPI application factory.

Run with:  uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI app instance."""
    settings = get_settings()
    configure_logging(level=settings.log_level)

    app = FastAPI(
        title="Landloads API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    log = get_logger("app.startup", env=settings.app_env)
    log.info("application_startup")

    app.include_router(health.router)

    return app
