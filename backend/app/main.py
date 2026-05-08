"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI app instance."""
    settings = get_settings()
    configure_logging(level=settings.log_level)

    app = FastAPI(
        title="Landloads API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    log = get_logger("app.startup", env=settings.app_env)
    log.info("application_startup")

    app.include_router(health.router, prefix="")

    return app


app = create_app()
