"""Payment-plan service: request, decide, default detection."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.invoices.models import Invoice
from app.invoices.state_machine import (
    PLAN_ELIGIBLE_STATES,
    IllegalStateError,
    next_status,
)
from app.leases.models import Lease
from app.plans.models import PaymentPlan, PaymentPlanStatus
from app.plans.schemas import Installment, PlanDecision, PlanRequest
from app.users.models import User


class PlanError(Exception):
    pass


class PlanNotFound(PlanError):
    pass


class PlanIneligible(PlanError):
    pass


def _serialise_schedule(items: list[Installment]) -> list[dict[str, Any]]:
    return [
        {
            "date": i.date.isoformat(),
            "amount": str(i.amount),
            "paid_payment_id": (
                str(i.paid_payment_id) if i.paid_payment_id else None
            ),
        }
        for i in items
    ]


def _schedule_total(items: list[Installment]) -> Decimal:
    return sum((i.amount for i in items), Decimal("0"))


async def _get_invoice_for_tenant(
    db: AsyncSession, *, tenant_id: uuid.UUID, invoice_id: uuid.UUID
) -> Invoice:
    stmt = (
        select(Invoice)
        .join(Lease, Lease.id == Invoice.lease_id)
        .where(Invoice.id == invoice_id, Lease.tenant_id == tenant_id)
    )
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if inv is None:
        raise PlanIneligible("invoice not found for tenant")
    return inv


async def request_plan(
    db: AsyncSession, *, tenant_id: uuid.UUID, body: PlanRequest
) -> PaymentPlan:
    invoice = await _get_invoice_for_tenant(
        db, tenant_id=tenant_id, invoice_id=body.invoice_id
    )
    if invoice.status not in PLAN_ELIGIBLE_STATES:
        raise PlanIneligible(
            f"invoice in state {invoice.status.value} not eligible for plan"
        )
    total = _schedule_total(body.schedule)
    outstanding = invoice.amount + invoice.late_fee_accrued
    if total < outstanding:
        raise PlanIneligible(
            f"plan total {total} less than outstanding {outstanding}"
        )

    plan = PaymentPlan(
        invoice_id=invoice.id,
        requested_at=datetime.now(tz=UTC),
        schedule=_serialise_schedule(body.schedule),
        status=PaymentPlanStatus.PENDING,
    )
    db.add(plan)
    await db.flush()
    return plan


async def decide_plan(
    db: AsyncSession,
    *,
    landlord: User,
    plan_id: uuid.UUID,
    body: PlanDecision,
) -> PaymentPlan:
    plan = await db.get(PaymentPlan, plan_id)
    if plan is None:
        raise PlanNotFound()
    if plan.status != PaymentPlanStatus.PENDING:
        raise PlanError("plan already decided")

    if body.action == "approve":
        plan.status = PaymentPlanStatus.APPROVED
        plan.approved_by = landlord.id
        plan.decided_at = datetime.now(tz=UTC)
        invoice = await db.get(Invoice, plan.invoice_id)
        if invoice is not None:
            try:
                invoice.status = next_status(invoice.status, "plan_approved")
            except IllegalStateError as exc:
                raise PlanError(str(exc)) from exc
        await audit.log(
            db,
            actor_id=landlord.id,
            action="plan.approve",
            entity_type="plan",
            entity_id=plan.id,
        )
    elif body.action == "reject":
        plan.status = PaymentPlanStatus.REJECTED
        plan.approved_by = landlord.id
        plan.decided_at = datetime.now(tz=UTC)
        plan.rejection_reason = body.reason or "rejected"
        await audit.log(
            db,
            actor_id=landlord.id,
            action="plan.reject",
            entity_type="plan",
            entity_id=plan.id,
            meta={"reason": body.reason},
        )
    else:  # counter
        if not body.counter_schedule:
            raise PlanError("counter requires counter_schedule")
        plan.schedule = _serialise_schedule(body.counter_schedule)
        # Stays PENDING — tenant must re-confirm by accepting (= a separate
        # endpoint or simply resending the same schedule).
        await audit.log(
            db,
            actor_id=landlord.id,
            action="plan.counter",
            entity_type="plan",
            entity_id=plan.id,
        )

    await db.flush()
    return plan


def _next_unpaid(schedule: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in schedule:
        if not item.get("paid_payment_id"):
            return item
    return None


async def detect_defaults(db: AsyncSession, *, today: date) -> int:
    """Iterate APPROVED plans and mark DEFAULTED if any past-due installment is unpaid 24h.

    Returns the number of plans defaulted.
    """
    rows = (
        await db.execute(
            select(PaymentPlan).where(PaymentPlan.status == PaymentPlanStatus.APPROVED)
        )
    ).scalars().all()
    n = 0
    for plan in rows:
        nxt = _next_unpaid(plan.schedule)
        if nxt is None:
            # All installments paid → completed.
            plan.status = PaymentPlanStatus.COMPLETED
            inv = await db.get(Invoice, plan.invoice_id)
            if inv is not None:
                try:
                    inv.status = next_status(inv.status, "plan_completed")
                except IllegalStateError:
                    pass
            continue
        due = date.fromisoformat(nxt["date"])
        if today >= due + timedelta(days=1):
            plan.status = PaymentPlanStatus.DEFAULTED
            inv = await db.get(Invoice, plan.invoice_id)
            if inv is not None:
                try:
                    inv.status = next_status(inv.status, "plan_installment_missed")
                except IllegalStateError:
                    pass
            n += 1
    await db.flush()
    return n


async def list_for_tenant(
    db: AsyncSession, *, tenant_id: uuid.UUID
) -> Sequence[PaymentPlan]:
    stmt = (
        select(PaymentPlan)
        .join(Invoice, Invoice.id == PaymentPlan.invoice_id)
        .join(Lease, Lease.id == Invoice.lease_id)
        .where(Lease.tenant_id == tenant_id)
        .order_by(PaymentPlan.created_at.desc())
    )
    return (await db.execute(stmt)).scalars().all()


async def list_for_landlord(
    db: AsyncSession,
    *,
    landlord: User,
    status_: PaymentPlanStatus | None = None,
) -> Sequence[PaymentPlan]:
    from app.properties.models import Property, Unit

    stmt = (
        select(PaymentPlan)
        .join(Invoice, Invoice.id == PaymentPlan.invoice_id)
        .join(Lease, Lease.id == Invoice.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .where(Property.landlord_id == landlord.id)
        .order_by(PaymentPlan.created_at.desc())
    )
    if status_ is not None:
        stmt = stmt.where(PaymentPlan.status == status_)
    return (await db.execute(stmt)).scalars().all()
