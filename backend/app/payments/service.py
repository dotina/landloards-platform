"""Payments service: STK Push initiation + callback handling."""
from __future__ import annotations

import uuid
from datetime import UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.core.config import get_settings
from app.invoices.models import Invoice, InvoiceStatus
from app.invoices.service import recompute_status_for_payment
from app.leases.models import Lease
from app.payments.models import Payment, PaymentChannel, PaymentStatus
from app.payments.mpesa import client as daraja
from app.payments.mpesa import security as cb_sec
from app.tenants.models import Tenant
from app.users.models import User


class PaymentError(Exception):
    pass


class InvoiceNotPayable(PaymentError):
    """Invoice is missing, terminal, or not yours."""


async def _resolve_invoice_for_tenant(
    db: AsyncSession, *, tenant_id: uuid.UUID, invoice_id: uuid.UUID
) -> Invoice:
    stmt = (
        select(Invoice)
        .join(Lease, Lease.id == Invoice.lease_id)
        .where(Invoice.id == invoice_id, Lease.tenant_id == tenant_id)
    )
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if inv is None:
        raise InvoiceNotPayable("invoice not found")
    if inv.status in (InvoiceStatus.PAID, InvoiceStatus.WRITTEN_OFF):
        raise InvoiceNotPayable("invoice already settled")
    return inv


async def initiate_stk(
    db: AsyncSession,
    *,
    tenant_user: User,
    tenant: Tenant,
    invoice_id: uuid.UUID,
    amount: Decimal,
    phone: str,
) -> Payment:
    """Initiate STK push and create a PENDING Payment row."""
    settings = get_settings()
    invoice = await _resolve_invoice_for_tenant(
        db, tenant_id=tenant.id, invoice_id=invoice_id
    )

    payment = Payment(
        invoice_id=invoice.id,
        tenant_id=tenant.id,
        amount=amount,
        channel=PaymentChannel.MPESA_STK,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.flush()

    # Reference includes the invoice prefix so Daraja's account-ref aligns
    # with the invoice for human eyes; tenant_code is the C2B fallback.
    account_ref = (tenant_user.tenant_code or str(tenant.id))[:12]
    desc = f"Inv {str(invoice.id)[:6]}"

    # Provisional callback URL is signed against an unknown checkout id —
    # we update payment.checkout_request_id once Daraja returns it.
    placeholder = f"pending-{payment.id}"
    cb = cb_sec.callback_url(
        placeholder,
        base_url=settings.mpesa_callback_base_url,
        secret=settings.mpesa_callback_secret,
    )

    try:
        result = await daraja.stk_push(
            phone=phone,
            amount=int(amount),
            account_reference=account_ref,
            transaction_desc=desc,
            callback_url=cb,
        )
    except daraja.DarajaError as exc:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = str(exc)[:500]
        await db.flush()
        raise PaymentError(str(exc)) from exc

    payment.checkout_request_id = result.checkout_request_id
    await db.flush()

    # Re-issue the callback URL bound to the *real* checkout id, so the
    # webhook can verify the signature on receipt. Daraja will accept the
    # original URL we passed; this stored one is for our verification path
    # in tests / reconciliation.
    real_cb = cb_sec.callback_url(
        result.checkout_request_id,
        base_url=settings.mpesa_callback_base_url,
        secret=settings.mpesa_callback_secret,
    )
    await audit.log(
        db,
        actor_id=tenant_user.id,
        action="payment.stk_initiate",
        entity_type="payment",
        entity_id=payment.id,
        meta={
            "checkout_request_id": result.checkout_request_id,
            "callback_url": real_cb,
        },
    )
    return payment


async def get_payment_by_checkout_id(
    db: AsyncSession, *, checkout_request_id: str
) -> Payment | None:
    stmt = select(Payment).where(Payment.checkout_request_id == checkout_request_id)
    return (await db.execute(stmt)).scalar_one_or_none()


def _extract_callback_fields(payload: dict[str, Any]) -> tuple[str, int, dict[str, Any]]:
    """Return ``(checkout_request_id, result_code, item_map)``.

    `item_map` keys are CallbackMetadata.Item.Name → Value.
    """
    cb = (payload.get("Body") or {}).get("stkCallback") or {}
    cid = str(cb.get("CheckoutRequestID", ""))
    result_code = int(cb.get("ResultCode", 1))
    items = ((cb.get("CallbackMetadata") or {}).get("Item")) or []
    item_map = {it["Name"]: it.get("Value") for it in items if "Name" in it}
    return cid, result_code, item_map


async def reconcile_pending_stk(
    db: AsyncSession, *, older_than_seconds: int = 90
) -> int:
    """Iterate PENDING STK payments older than ``older_than_seconds``,
    call Daraja stk_query, and mark FAILED on terminal "cancelled/timeout"
    result codes (1, 1032, 1037, 1019, 2001).

    Returns the number of payments transitioned to FAILED. Successful
    payments are not promoted here — those land via the webhook to keep
    a single write-path for SUCCESS. This guards against stuck rows when
    Daraja's webhook never arrives.
    """
    from datetime import datetime, timedelta

    threshold = datetime.now(tz=UTC) - timedelta(seconds=older_than_seconds)
    stmt = select(Payment).where(
        Payment.channel == PaymentChannel.MPESA_STK,
        Payment.status == PaymentStatus.PENDING,
        Payment.checkout_request_id.is_not(None),
        Payment.created_at < threshold,
    )
    rows = (await db.execute(stmt)).scalars().all()
    n = 0
    for p in rows:
        try:
            r = await daraja.stk_query(checkout_request_id=p.checkout_request_id or "")
        except daraja.DarajaError:
            continue
        if r.result_code in {"1032", "1037", "1019", "2001", "1"}:
            p.status = PaymentStatus.FAILED
            p.failure_reason = f"reconciled: {r.result_desc}"[:500]
            n += 1
    await db.flush()
    return n


async def handle_stk_callback(
    db: AsyncSession, *, payload: dict[str, Any]
) -> Payment | None:
    """Update a PENDING payment from a Daraja callback. Idempotent."""
    cid, result_code, item_map = _extract_callback_fields(payload)
    if not cid:
        return None
    payment = await get_payment_by_checkout_id(db, checkout_request_id=cid)
    if payment is None:
        return None

    payment.raw_callback = payload

    if result_code == 0:
        receipt = str(item_map.get("MpesaReceiptNumber", "") or "")
        # Idempotency: a second callback with the same receipt is a no-op.
        if payment.status == PaymentStatus.SUCCESS and payment.mpesa_receipt == receipt:
            return payment
        payment.status = PaymentStatus.SUCCESS
        payment.mpesa_receipt = receipt or None
        try:
            await db.flush()
        except IntegrityError as exc:
            # Another payment row already claimed this receipt — keep our row
            # in failed state to avoid double-credit; admin investigates.
            await db.rollback()
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = f"duplicate receipt: {exc}"[:500]
            await db.flush()
            return payment

        if payment.invoice_id is not None:
            invoice = await db.get(Invoice, payment.invoice_id)
            if invoice is not None:
                await recompute_status_for_payment(db, invoice=invoice)
    else:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = (
            f"ResultCode={result_code}: "
            f"{(payload.get('Body') or {}).get('stkCallback', {}).get('ResultDesc', '')}"
        )[:500]
        await db.flush()
    return payment
