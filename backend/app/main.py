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
from app.notifications.router import router as notifications_router
from app.payments.c2b_router import admin_router as c2b_admin_router
from app.payments.c2b_router import webhooks_router as c2b_webhooks_router
from app.payments.router import admin_router as payments_admin_router
from app.payments.router import router as payments_router
from app.payments.router import webhooks_router as payments_webhooks_router
from app.plans.router import admin_router as plans_admin_router
from app.plans.router import tenant_router as plans_tenant_router
from app.receipts.router import admin_router as receipts_admin_router
from app.receipts.router import router as receipts_router
from app.receipts.router import tenant_router as receipts_tenant_router
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
    app.include_router(notifications_router)
    app.include_router(payments_router)
    app.include_router(payments_admin_router)
    app.include_router(payments_webhooks_router)
    app.include_router(c2b_webhooks_router)
    app.include_router(c2b_admin_router)
    app.include_router(plans_tenant_router)
    app.include_router(plans_admin_router)
    app.include_router(receipts_router)
    app.include_router(receipts_admin_router)
    app.include_router(receipts_tenant_router)

    from app.payments.router import tenant_router as payments_tenant_router
    from app.leases.router import tenant_router as leases_tenant_router
    from app.notifications.router import tenant_router as notifications_tenant_router

    app.include_router(payments_tenant_router)
    app.include_router(leases_tenant_router)
    app.include_router(notifications_tenant_router)

    return app
