"""FastAPI application factory.

Run with:  uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.properties.router import router as properties_router
from app.properties.router import units_router as units_router
from app.invoices.router import admin_router as invoices_admin_router
from app.invoices.router import landlord_router as invoices_landlord_router
from app.invoices.router import tenant_invoices_router
from app.leases.router import router as leases_router
from app.tenants.router import admin_router as tenants_admin_router
from app.tenants.router import tenant_router as tenants_tenant_router


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
    app.include_router(auth_router)
    app.include_router(properties_router)
    app.include_router(units_router)
    app.include_router(tenants_tenant_router)
    app.include_router(tenants_admin_router)
    app.include_router(leases_router)
    app.include_router(invoices_landlord_router)
    app.include_router(invoices_admin_router)
    app.include_router(tenant_invoices_router)

    return app
