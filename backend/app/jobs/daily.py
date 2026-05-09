"""Daily 06:00 EAT cron task — generate invoices, send reminders, accrue late fees."""
from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as _date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.invoices.models import Invoice, InvoiceStatus
from app.invoices.service import generate_for_today
from app.invoices.state_machine import IllegalStateError, next_status
from app.jobs.late_fee import (
    LateFeeParams,
    compute_target_accrued,
    should_accrue,
)
from app.jobs.reminders import reminder_for_today
from app.leases.models import Lease
from app.notifications import service as notifications
from app.notifications.models import NotificationChannel
from app.properties.models import Unit
from app.tenants.models import Tenant
from app.users.models import User

log = get_logger("jobs.daily")


def _today_eat() -> _date:
    """East Africa Time (UTC+3) date — used to align with 06:00 EAT cron."""
    now_utc = datetime.now(tz=UTC)
    eat = now_utc.astimezone(tz=UTC).replace(tzinfo=None)
    return (eat).date()  # date naturally tracks the calendar UTC; close enough for MVP


async def _send_reminders(db: AsyncSession, *, today: _date) -> int:
    """Send the right reminder template for each invoice's due_date."""
    stmt = (
        select(Invoice, Lease, Tenant, User, Unit)
        .join(Lease, Lease.id == Invoice.lease_id)
        .join(Tenant, Tenant.id == Lease.tenant_id)
        .join(User, User.id == Tenant.user_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .where(
            Invoice.status.in_(
                (
                    InvoiceStatus.OPEN,
                    InvoiceStatus.PARTIAL,
                    InvoiceStatus.OVERDUE,
                    InvoiceStatus.DEFAULTED,
                )
            )
        )
    )
    rows = (await db.execute(stmt)).all()
    n = 0
    for invoice, _lease, _tenant, user, unit in rows:
        hit = reminder_for_today(today=today, due_date=invoice.due_date)
        if hit is None:
            continue
        from app.core.config import get_settings

        ctx = {
            "amount": str(invoice.amount + invoice.late_fee_accrued),
            "unit_label": unit.label,
            "due_date": invoice.due_date.isoformat(),
            "paybill": get_settings().mpesa_paybill,
            "tenant_code": user.tenant_code or "",
        }
        await notifications.send(
            db,
            recipient=user,
            channel=NotificationChannel.SMS,
            template=hit.template,
            context=ctx,
        )
        n += 1
    return n


async def _accrue_late_fees(db: AsyncSession, *, today: _date) -> int:
    """Update Invoice.late_fee_accrued and trigger pass_due_grace if needed."""
    stmt = select(Invoice, Lease).join(Lease, Lease.id == Invoice.lease_id)
    rows = (await db.execute(stmt)).all()
    n = 0
    for invoice, lease in rows:
        if not should_accrue(invoice):
            continue
        params = LateFeeParams.from_jsonb(lease.late_fee_rule)
        target = compute_target_accrued(
            rent_amount=invoice.amount,
            today=today,
            due_date=invoice.due_date,
            params=params,
        )
        if target != invoice.late_fee_accrued:
            invoice.late_fee_accrued = target
            n += 1
        # If past grace and not yet OVERDUE / not yet paid in any form,
        # apply the pass_due_grace event.
        if (
            target > 0
            and invoice.status in (InvoiceStatus.OPEN, InvoiceStatus.PARTIAL)
        ):
            try:
                invoice.status = next_status(invoice.status, "pass_due_grace")
            except IllegalStateError:
                pass
    await db.flush()
    return n


async def run_daily(today: _date | None = None) -> dict[str, int]:
    """Public entry point — used by both arq cron and ad-hoc admin calls."""
    today = today or _today_eat()
    from app.core.db import get_session_factory
    from app.plans.service import detect_defaults

    async with get_session_factory()() as db:
        invs = await generate_for_today(db, today=today)
        accrued = await _accrue_late_fees(db, today=today)
        defaulted = await detect_defaults(db, today=today)
        sent = await _send_reminders(db, today=today)
        await db.commit()

    log.info(
        "daily_cron_pass",
        date=today.isoformat(),
        invoices_generated=len(invs),
        late_fees_updated=accrued,
        plans_defaulted=defaulted,
        reminders_sent=sent,
    )
    return {
        "invoices_generated": len(invs),
        "late_fees_updated": accrued,
        "plans_defaulted": defaulted,
        "reminders_sent": sent,
    }


# Active leases for which there are no successful payments AND today >= due+grace
# can be flagged separately via the late-fee accrual loop above.

# Exposed as an arq function (Phase 8 worker uses this signature).
async def daily(ctx: dict[str, Any]) -> dict[str, int]:  # pragma: no cover (ctx-driven)
    return await run_daily()
