"""HTTP routes for invoices."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord, require_tenant
from app.invoices import service
from app.invoices.models import InvoiceStatus
from app.invoices.schemas import InvoiceOut, InvoiceWriteOffRequest
from app.tenants.service import get_tenant_by_user_id
from app.users.models import User

landlord_router = APIRouter(prefix="/invoices", tags=["invoices"])


@landlord_router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
    status_: InvoiceStatus | None = Query(default=None, alias="status"),
    lease_id: uuid.UUID | None = None,
) -> list[InvoiceOut]:
    items = await service.list_invoices_for_landlord(
        db, landlord=landlord, status_=status_, lease_id=lease_id
    )
    return [InvoiceOut.model_validate(i) for i in items]


@landlord_router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> InvoiceOut:
    try:
        inv = await service.get_invoice_for_landlord(
            db, landlord=landlord, invoice_id=invoice_id
        )
    except service.InvoiceNotFound:
        raise HTTPException(status_code=404, detail="invoice not found")
    return InvoiceOut.model_validate(inv)


admin_router = APIRouter(prefix="/admin/invoices", tags=["admin-invoices"])


@admin_router.post("/{invoice_id}/write-off", response_model=InvoiceOut)
async def write_off(
    invoice_id: uuid.UUID,
    body: InvoiceWriteOffRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> InvoiceOut:
    try:
        inv = await service.write_off(
            db, landlord=landlord, invoice_id=invoice_id, reason=body.reason
        )
    except service.InvoiceNotFound:
        raise HTTPException(status_code=404, detail="invoice not found")
    except service.InvoiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return InvoiceOut.model_validate(inv)


# Tenant-side
tenant_invoices_router = APIRouter(prefix="/tenant/invoices", tags=["tenant-invoices"])


@tenant_invoices_router.get("", response_model=list[InvoiceOut])
async def my_invoices(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
    status_: InvoiceStatus | None = Query(default=None, alias="status"),
) -> list[InvoiceOut]:
    tenant = await get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant profile not found")
    items = await service.list_invoices_for_tenant(
        db, tenant_id=tenant.id, status_=status_
    )
    return [InvoiceOut.model_validate(i) for i in items]
