"""C2B Paybill confirmation handling.

Inbound Daraja payload shape (validate + confirm share schema):

    {
      "TransID": "OEI2AK4Q16",
      "TransAmount": "12345.0",
      "BusinessShortCode": "600000",
      "BillRefNumber": "ABC123",
      "MSISDN": "254712345678",
      "TransTime": "20191122063845",
      ...
    }

`BillRefNumber` is the account reference the customer typed in M-Pesa.
We try to resolve it to a User.tenant_code; if successful we create a
SUCCESS Payment and recompute the oldest unpaid invoice. If not, we
park the raw payload in unmatched_c2b for landlord manual allocation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.invoices.models import Invoice, InvoiceStatus
from app.invoices.service import recompute_status_for_payment
from app.leases.models import Lease
from app.payments.c2b_models import UnmatchedC2B
from app.payments.models import Payment, PaymentChannel, PaymentStatus
from app.tenants.models import Tenant
from app.users.models import User, UserRole


def _safe_decimal(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _parse_trans_time(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    except Exception:
        return None


async def _find_oldest_open_invoice_for_tenant(
    db: AsyncSession, *, tenant_id: uuid.UUID
) -> Invoice | None:
    stmt = (
        select(Invoice)
        .join(Lease, Lease.id == Invoice.lease_id)
        .where(
            Lease.tenant_id == tenant_id,
            Invoice.status.in_(
                (
                    InvoiceStatus.OPEN,
                    InvoiceStatus.PARTIAL,
                    InvoiceStatus.OVERDUE,
                    InvoiceStatus.ON_PAY_PLAN,
                    InvoiceStatus.DEFAULTED,
                )
            ),
        )
        .order_by(Invoice.due_date.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _resolve_tenant_for_bill_ref(
    db: AsyncSession, *, bill_ref: str | None
) -> tuple[User, Tenant] | None:
    if not bill_ref:
        return None
    code = bill_ref.strip().upper()
    user = (await db.execute(
        select(User).where(User.tenant_code == code, User.role == UserRole.TENANT)
    )).scalar_one_or_none()
    if user is None:
        return None
    tenant = (await db.execute(
        select(Tenant).where(Tenant.user_id == user.id)
    )).scalar_one_or_none()
    if tenant is None:
        return None
    return user, tenant


async def handle_c2b_confirm(
    db: AsyncSession, *, payload: dict[str, Any]
) -> tuple[str, uuid.UUID | None]:
    """Process a Daraja C2B confirmation. Idempotent on TransID/MpesaReceipt.

    Returns ``(outcome, payment_or_unmatched_id)`` where outcome is one of
    "matched", "unmatched", "duplicate".
    """
    receipt = str(payload.get("TransID") or "").strip()
    if not receipt:
        return "unmatched", None
    amount = _safe_decimal(payload.get("TransAmount"))
    msisdn = str(payload.get("MSISDN") or "")
    bill_ref = (payload.get("BillRefNumber") or None) and str(payload["BillRefNumber"])
    trans_time = _parse_trans_time(payload.get("TransTime"))

    # Idempotency: if we've already recorded this receipt, no-op.
    existing = (await db.execute(
        select(Payment).where(
            Payment.channel == PaymentChannel.MPESA_C2B,
            Payment.mpesa_receipt == receipt,
        )
    )).scalar_one_or_none()
    if existing is not None:
        return "duplicate", existing.id

    existing_unmatched = (await db.execute(
        select(UnmatchedC2B).where(UnmatchedC2B.mpesa_receipt == receipt)
    )).scalar_one_or_none()
    if existing_unmatched is not None:
        return "duplicate", existing_unmatched.id

    resolved = await _resolve_tenant_for_bill_ref(db, bill_ref=bill_ref)
    if resolved is None:
        u = UnmatchedC2B(
            mpesa_receipt=receipt,
            bill_ref=bill_ref,
            msisdn=msisdn,
            amount=amount,
            transaction_time=trans_time,
            raw=payload,
        )
        db.add(u)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return "duplicate", None
        return "unmatched", u.id

    _user, tenant = resolved
    invoice = await _find_oldest_open_invoice_for_tenant(db, tenant_id=tenant.id)
    payment = Payment(
        invoice_id=invoice.id if invoice is not None else None,
        tenant_id=tenant.id,
        amount=amount,
        channel=PaymentChannel.MPESA_C2B,
        status=PaymentStatus.SUCCESS,
        mpesa_receipt=receipt,
        raw_callback=payload,
    )
    db.add(payment)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return "duplicate", None

    if invoice is not None:
        await recompute_status_for_payment(db, invoice=invoice)

    await audit.log(
        db,
        actor_id=None,
        action="payment.c2b_confirm",
        entity_type="payment",
        entity_id=payment.id,
        meta={
            "mpesa_receipt": receipt,
            "bill_ref": bill_ref,
            "tenant_id": str(tenant.id),
            "invoice_id": str(invoice.id) if invoice else None,
        },
    )
    return "matched", payment.id


async def allocate_unmatched(
    db: AsyncSession,
    *,
    actor: User,
    unmatched_id: uuid.UUID,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID | None,
) -> Payment:
    """Convert an unmatched_c2b row into a Payment row attached to the
    chosen tenant (and optionally a specific invoice).
    """
    u = await db.get(UnmatchedC2B, unmatched_id)
    if u is None or u.is_allocated:
        raise ValueError("unmatched row not found or already allocated")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant not found")

    invoice: Invoice | None = None
    if invoice_id is not None:
        invoice = await db.get(Invoice, invoice_id)
        if invoice is None:
            raise ValueError("invoice not found")

    payment = Payment(
        invoice_id=invoice.id if invoice else None,
        tenant_id=tenant.id,
        amount=u.amount,
        channel=PaymentChannel.MPESA_C2B,
        status=PaymentStatus.SUCCESS,
        mpesa_receipt=u.mpesa_receipt,
        raw_callback=u.raw,
    )
    db.add(payment)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError(f"duplicate receipt: {exc}") from exc

    u.is_allocated = True
    u.allocated_payment_id = payment.id

    if invoice is not None:
        await recompute_status_for_payment(db, invoice=invoice)

    await audit.log(
        db,
        actor_id=actor.id,
        action="payment.c2b_allocate",
        entity_type="payment",
        entity_id=payment.id,
        meta={
            "unmatched_id": str(u.id),
            "tenant_id": str(tenant.id),
            "invoice_id": str(invoice.id) if invoice else None,
        },
    )
    return payment
