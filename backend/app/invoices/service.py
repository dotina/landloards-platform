"""Invoice generation + status recompute service."""
from __future__ import annotations

import calendar
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.invoices.models import Invoice, InvoiceStatus
from app.invoices.state_machine import (
    IllegalStateError,
    InvoiceEvent,
    next_status,
)
from app.leases.models import Lease, LeaseStatus
from app.payments.models import Payment, PaymentStatus
from app.properties.models import Property, Unit
from app.users.models import User, UserRole


class InvoiceError(Exception):
    pass


class InvoiceNotFound(InvoiceError):
    pass


# ─── Helpers ─────────────────────────────────────────────────────────
def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def compute_period_for(*, today: date, due_day: int) -> tuple[date, date, date]:
    """Return ``(period_start, period_end, due_date)`` for the period that
    contains ``today`` for a lease whose ``due_day_of_month`` is ``due_day``.

    Periods run [1st, last-of-month] regardless of due_day; the due_date is
    clamped to the last day of the month if due_day > 28 isn't valid.
    """
    period_start = date(today.year, today.month, 1)
    period_end = date(
        today.year, today.month, _last_day_of_month(today.year, today.month)
    )
    clamped_day = min(due_day, _last_day_of_month(today.year, today.month))
    due_date = date(today.year, today.month, clamped_day)
    return period_start, period_end, due_date


# ─── Generation ──────────────────────────────────────────────────────
async def generate_for_today(db: AsyncSession, *, today: date) -> list[Invoice]:
    """Idempotently create rent invoices for any active lease where the
    current month's ``due_day_of_month`` equals ``today.day`` (or where
    ``today`` >= due_day and the period invoice doesn't yet exist).
    """
    # Pull active leases with their unit's due_day_of_month.
    stmt = (
        select(Lease, Unit.due_day_of_month)
        .join(Unit, Unit.id == Lease.unit_id)
        .where(Lease.status == LeaseStatus.ACTIVE)
    )
    rows = (await db.execute(stmt)).all()

    created: list[Invoice] = []
    for lease, due_day in rows:
        period_start, period_end, due_date = compute_period_for(today=today, due_day=due_day)

        # Honour lease end_date: don't generate past lease.end_date.
        if lease.end_date is not None and period_start > lease.end_date:
            continue

        inv = Invoice(
            lease_id=lease.id,
            period_start=period_start,
            period_end=period_end,
            due_date=due_date,
            amount=lease.rent_amount,
            late_fee_accrued=Decimal("0"),
            status=InvoiceStatus.OPEN,
        )
        db.add(inv)
        try:
            await db.flush()
            created.append(inv)
        except IntegrityError:
            # Duplicate (lease_id, period_start) — already generated this period.
            await db.rollback()
    return created


# ─── State recompute (called from payments + plans) ──────────────────
async def successful_payments_total(
    db: AsyncSession, *, invoice_id: uuid.UUID
) -> Decimal:
    stmt = select(Payment).where(
        Payment.invoice_id == invoice_id,
        Payment.status == PaymentStatus.SUCCESS,
    )
    rows = (await db.execute(stmt)).scalars().all()
    total = Decimal("0")
    for p in rows:
        total += p.amount
    return total


async def recompute_status_for_payment(
    db: AsyncSession, *, invoice: Invoice
) -> Invoice:
    """Recompute invoice status from its payments. Raises on illegal moves."""
    paid = await successful_payments_total(db, invoice_id=invoice.id)
    outstanding = invoice.amount + invoice.late_fee_accrued - paid

    if outstanding <= Decimal("0"):
        event: InvoiceEvent = "full_pay"
    elif paid > Decimal("0"):
        event = "partial_pay"
    else:
        # No successful payments yet — leave status alone.
        return invoice

    try:
        invoice.status = next_status(invoice.status, event)
    except IllegalStateError:
        # Terminal/written-off etc. — payments can land but state stays put.
        return invoice
    await db.flush()
    return invoice


# ─── Queries ─────────────────────────────────────────────────────────
async def list_invoices_for_landlord(
    db: AsyncSession,
    *,
    landlord: User,
    status_: Optional[InvoiceStatus] = None,
    lease_id: Optional[uuid.UUID] = None,
) -> Sequence[Invoice]:
    stmt = (
        select(Invoice)
        .join(Lease, Lease.id == Invoice.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .where(Property.landlord_id == landlord.id)
        .order_by(Invoice.due_date.desc())
    )
    if status_ is not None:
        stmt = stmt.where(Invoice.status == status_)
    if lease_id is not None:
        stmt = stmt.where(Invoice.lease_id == lease_id)
    return (await db.execute(stmt)).scalars().all()


async def list_invoices_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    status_: Optional[InvoiceStatus] = None,
) -> Sequence[Invoice]:
    stmt = (
        select(Invoice)
        .join(Lease, Lease.id == Invoice.lease_id)
        .where(Lease.tenant_id == tenant_id)
        .order_by(Invoice.due_date.desc())
    )
    if status_ is not None:
        stmt = stmt.where(Invoice.status == status_)
    return (await db.execute(stmt)).scalars().all()


async def get_invoice_for_landlord(
    db: AsyncSession, *, landlord: User, invoice_id: uuid.UUID
) -> Invoice:
    stmt = (
        select(Invoice)
        .join(Lease, Lease.id == Invoice.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .where(Invoice.id == invoice_id, Property.landlord_id == landlord.id)
    )
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if inv is None:
        raise InvoiceNotFound()
    return inv


# ─── Write-off (admin action) ────────────────────────────────────────
async def write_off(
    db: AsyncSession, *, landlord: User, invoice_id: uuid.UUID, reason: str
) -> Invoice:
    if landlord.role not in (UserRole.LANDLORD, UserRole.ADMIN):
        raise InvoiceError("only landlord may write off")
    inv = await get_invoice_for_landlord(db, landlord=landlord, invoice_id=invoice_id)

    try:
        inv.status = next_status(inv.status, "write_off")
    except IllegalStateError as exc:
        raise InvoiceError(str(exc)) from exc

    inv.write_off_reason = reason
    await audit.log(
        db,
        actor_id=landlord.id,
        action="invoice.write_off",
        entity_type="invoice",
        entity_id=inv.id,
        meta={"reason": reason},
    )
    await db.flush()
    return inv


def event_for_due_grace_pass(today: date, due_date: date, grace_days: int) -> Iterable[InvoiceEvent]:
    """Yield the ``pass_due_grace`` event iff appropriate."""
    if today >= due_date + timedelta(days=grace_days):
        yield "pass_due_grace"
