"""HTTP routes for C2B Paybill webhooks + unmatched-allocation admin."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord
from app.core.logging import get_logger
from app.payments import c2b
from app.payments.c2b_models import UnmatchedC2B
from app.users.models import User

log = get_logger("payments.c2b")


# ─── Webhook routes (Daraja) ─────────────────────────────────────────
webhooks_router = APIRouter(prefix="/webhooks/mpesa/c2b", tags=["webhooks-mpesa-c2b"])


@webhooks_router.post("/validate", response_model=dict)
async def c2b_validate(request: Request) -> dict[str, Any]:
    """Daraja validation hook — accept all by default.

    A merchant could plug stricter validation here (e.g. unknown account
    refs rejected up-front), but doing so risks losing legitimate edge
    cases. Confirmation handler is where allocation lives.
    """
    body = await request.json()
    log.info("c2b_validate", bill_ref=body.get("BillRefNumber"))
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@webhooks_router.post("/confirm", response_model=dict)
async def c2b_confirm(
    request: Request,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> dict[str, Any]:
    payload = await request.json()
    outcome, _ref_id = await c2b.handle_c2b_confirm(db, payload=payload)
    await db.commit()
    log.info(
        "c2b_confirm",
        outcome=outcome,
        bill_ref=payload.get("BillRefNumber"),
        receipt=payload.get("TransID"),
    )
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


# ─── Admin-side unmatched queue ──────────────────────────────────────
class UnmatchedOut(BaseModel):
    id: uuid.UUID
    mpesa_receipt: str
    bill_ref: str | None
    msisdn: str
    amount: float
    transaction_time: str | None
    is_allocated: bool

    model_config = ConfigDict(from_attributes=True)


class AllocateRequest(BaseModel):
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID | None = None


admin_router = APIRouter(prefix="/admin/payments/c2b", tags=["admin-payments-c2b"])


@admin_router.get("/unmatched", response_model=list[UnmatchedOut])
async def list_unmatched(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> list[UnmatchedOut]:
    rows = (
        await db.execute(
            select(UnmatchedC2B)
            .where(UnmatchedC2B.is_allocated.is_(False))
            .order_by(UnmatchedC2B.created_at.desc())
        )
    ).scalars().all()
    return [
        UnmatchedOut(
            id=r.id,
            mpesa_receipt=r.mpesa_receipt,
            bill_ref=r.bill_ref,
            msisdn=r.msisdn,
            amount=float(r.amount),
            transaction_time=r.transaction_time.isoformat() if r.transaction_time else None,
            is_allocated=r.is_allocated,
        )
        for r in rows
    ]


@admin_router.post("/unmatched/{unmatched_id}/allocate")
async def allocate(
    unmatched_id: uuid.UUID,
    body: AllocateRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> dict[str, str]:
    try:
        payment = await c2b.allocate_unmatched(
            db,
            actor=landlord,
            unmatched_id=unmatched_id,
            tenant_id=body.tenant_id,
            invoice_id=body.invoice_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {"payment_id": str(payment.id)}
