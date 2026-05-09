"""HTTP routes for STK Push initiation, status polling, and callbacks."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord, require_tenant
from app.core.config import get_settings
from app.core.logging import get_logger
from app.payments import service
from app.payments.mpesa.security import parse_token
from app.payments.schemas import (
    PaymentOut,
    StkInitiateRequest,
    StkInitiateResponse,
)
from app.tenants.service import get_tenant_by_user_id
from app.users.models import User

log = get_logger("payments")

# Tenant-side
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/stk/initiate", response_model=StkInitiateResponse)
async def initiate_stk(
    body: StkInitiateRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> StkInitiateResponse:
    tenant = await get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant profile not found")
    try:
        payment = await service.initiate_stk(
            db,
            tenant_user=user,
            tenant=tenant,
            invoice_id=body.invoice_id,
            amount=body.amount,
            phone=body.phone,
        )
    except service.InvoiceNotPayable as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except service.PaymentError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    await db.commit()
    return StkInitiateResponse(
        payment_id=payment.id,
        checkout_request_id=payment.checkout_request_id or "",
        status=payment.status.value,
    )


@router.get("/stk/{checkout_request_id}", response_model=PaymentOut)
async def stk_status(
    checkout_request_id: str,
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> PaymentOut:
    payment = await service.get_payment_by_checkout_id(
        db, checkout_request_id=checkout_request_id
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    tenant = await get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None or payment.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="payment not found")
    return PaymentOut.model_validate(payment)


tenant_router = APIRouter(prefix="/tenant/payments", tags=["tenant-payments"])


@tenant_router.get("", response_model=list[PaymentOut])
async def list_my_payments(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> list[PaymentOut]:
    from sqlalchemy import select

    from app.payments.models import Payment

    tenant = await get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        return []
    rows = (
        await db.execute(
            select(Payment)
            .where(Payment.tenant_id == tenant.id)
            .order_by(Payment.created_at.desc())
        )
    ).scalars().all()
    return [PaymentOut.model_validate(r) for r in rows]


# Landlord/admin
admin_router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])


@admin_router.get("", response_model=list[PaymentOut])
async def list_payments_admin(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],  # noqa: ARG001
) -> list[PaymentOut]:
    from sqlalchemy import select

    from app.payments.models import Payment

    rows = (
        await db.execute(select(Payment).order_by(Payment.created_at.desc()))
    ).scalars().all()
    return [PaymentOut.model_validate(r) for r in rows]


# Public webhook
webhooks_router = APIRouter(prefix="/webhooks/mpesa", tags=["webhooks-mpesa"])


@webhooks_router.post(
    "/stk/{token}", status_code=status.HTTP_200_OK, response_model=dict
)
async def stk_callback(
    request: Request,
    db: Annotated[AsyncSession, Depends(db_session)],
    token: str = Path(...),
) -> dict[str, Any]:
    settings = get_settings()
    expected_cid = parse_token(token, secret=settings.mpesa_callback_secret)
    if expected_cid is None:
        log.warning("mpesa_callback_bad_token")
        # Daraja expects a 200 even on rejection; reply with the canonical shape.
        return {"ResultCode": 1, "ResultDesc": "rejected"}

    payload: dict[str, Any] = await request.json()
    cb_cid = (
        ((payload.get("Body") or {}).get("stkCallback") or {}).get("CheckoutRequestID")
    )
    if cb_cid != expected_cid and not expected_cid.startswith("pending-"):
        # Daraja-driven path: the path token must agree with body.
        log.warning(
            "mpesa_callback_cid_mismatch",
            path_cid=expected_cid,
            body_cid=cb_cid,
        )
        return {"ResultCode": 1, "ResultDesc": "mismatch"}

    payment = await service.handle_stk_callback(db, payload=payload)
    await db.commit()

    log.info(
        "mpesa_callback_processed",
        checkout_request_id=cb_cid,
        payment_id=str(payment.id) if payment else None,
        status=payment.status.value if payment else "unknown",
    )
    return {"ResultCode": 0, "ResultDesc": "ok"}
